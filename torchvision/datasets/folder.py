import aiofiles
import asyncio
import io

from zipfile import ZipFile
import tarfile
import pickle
from .vision import VisionDataset

from PIL import Image

import os
import os.path
from typing import Any, Callable, cast, Dict, List, Optional, Tuple
import time


def has_file_allowed_extension(filename: str, extensions: Tuple[str, ...]) -> bool:
    """Checks if a file is an allowed extension.

    Args:
        filename (string): path to a file
        extensions (tuple of strings): extensions to consider (lowercase)

    Returns:
        bool: True if the filename ends with one of given extensions
    """
    return filename.lower().endswith(extensions)


def is_image_file(filename: str) -> bool:
    """Checks if a file is an allowed image extension.

    Args:
        filename (string): path to a file

    Returns:
        bool: True if the filename ends with a known image extension
    """
    return has_file_allowed_extension(filename, IMG_EXTENSIONS)


def make_dataset(
    directory: str,
    class_to_idx: Dict[str, int],
    extensions: Optional[Tuple[str, ...]] = None,
    is_valid_file: Optional[Callable[[str], bool]] = None,
) -> List[Tuple[str, int]]:
    """Generates a list of samples of a form (path_to_sample, class).

    Args:
        directory (str): root dataset directory
        class_to_idx (Dict[str, int]): dictionary mapping class name to class index
        extensions (optional): A list of allowed extensions.
            Either extensions or is_valid_file should be passed. Defaults to None.
        is_valid_file (optional): A function that takes path of a file
            and checks if the file is a valid file
            (used to check of corrupt files) both extensions and
            is_valid_file should not be passed. Defaults to None.

    Raises:
        ValueError: In case ``extensions`` and ``is_valid_file`` are None or both are not None.

    Returns:
        List[Tuple[str, int]]: samples of a form (path_to_sample, class)
    """
    instances = []
    directory = os.path.expanduser(directory)
    both_none = extensions is None and is_valid_file is None
    both_something = extensions is not None and is_valid_file is not None
    if both_none or both_something:
        raise ValueError("Both extensions and is_valid_file cannot be None or not None at the same time")
    if extensions is not None:
        def is_valid_file(x: str) -> bool:
            return has_file_allowed_extension(x, cast(Tuple[str, ...], extensions))
    is_valid_file = cast(Callable[[str], bool], is_valid_file)
    for target_class in sorted(class_to_idx.keys()):
        class_index = class_to_idx[target_class]
        target_dir = os.path.join(directory, target_class)
        if not os.path.isdir(target_dir):
            continue
        for root, _, fnames in sorted(os.walk(target_dir, followlinks=True)):
            for fname in sorted(fnames):
                path = os.path.join(root, fname)
                if is_valid_file(path):
                    item = path, class_index
                    instances.append(item)
    return instances


class DatasetFolder(VisionDataset):
    """A generic data loader where the samples are arranged in this way: ::

        root/class_x/xxx.ext
        root/class_x/xxy.ext
        root/class_x/[...]/xxz.ext

        root/class_y/123.ext
        root/class_y/nsdf3.ext
        root/class_y/[...]/asd932_.ext

    Args:
        root (string): Root directory path.
        loader (callable): A function to load a sample given its path.
        extensions (tuple[string]): A list of allowed extensions.
            both extensions and is_valid_file should not be passed.
        transform (callable, optional): A function/transform that takes in
            a sample and returns a transformed version.
            E.g, ``transforms.RandomCrop`` for images.
        target_transform (callable, optional): A function/transform that takes
            in the target and transforms it.
        is_valid_file (callable, optional): A function that takes path of a file
            and check if the file is a valid file (used to check of corrupt files)
            both extensions and is_valid_file should not be passed.

     Attributes:
        classes (list): List of the class names sorted alphabetically.
        class_to_idx (dict): Dict with items (class_name, class_index).
        samples (list): List of (sample path, class_index) tuples
        targets (list): The class_index value for each image in the dataset
    """

    def __init__(
            self,
            root: str,
            loader: Callable[[str], Any],
            extensions: Optional[Tuple[str, ...]] = None,
            transform: Optional[Callable] = None,
            target_transform: Optional[Callable] = None,
            is_valid_file: Optional[Callable[[str], bool]] = None,
    ) -> None:
        super(DatasetFolder, self).__init__(root, transform=transform,
                                            target_transform=target_transform)
        classes, class_to_idx = self._find_classes(self.root)
        samples = self.make_dataset(self.root, class_to_idx, extensions, is_valid_file)
        if len(samples) == 0:
            msg = "Found 0 files in subfolders of: {}\n".format(self.root)
            if extensions is not None:
                msg += "Supported extensions are: {}".format(",".join(extensions))
            raise RuntimeError(msg)

        self.loader = loader
        self.extensions = extensions

        self.classes = classes
        self.class_to_idx = class_to_idx
        self.samples = samples
        self.targets = [s[1] for s in samples]

    @staticmethod
    def make_dataset(
        directory: str,
        class_to_idx: Dict[str, int],
        extensions: Optional[Tuple[str, ...]] = None,
        is_valid_file: Optional[Callable[[str], bool]] = None,
    ) -> List[Tuple[str, int]]:
        return make_dataset(directory, class_to_idx, extensions=extensions, is_valid_file=is_valid_file)

    def _find_classes(self, dir: str) -> Tuple[List[str], Dict[str, int]]:
        """
        Finds the class folders in a dataset.

        Args:
            dir (string): Root directory path.

        Returns:
            tuple: (classes, class_to_idx) where classes are relative to (dir), and class_to_idx is a dictionary.

        Ensures:
            No class is a subdirectory of another.
        """
        classes = [d.name for d in os.scandir(dir) if d.is_dir()]
        classes.sort()
        class_to_idx = {cls_name: i for i, cls_name in enumerate(classes)}
        return classes, class_to_idx

    def __getitem__(self, index: int) -> Tuple[Any, Any]:
        """
        Args:
            index (int): Index

        Returns:
            tuple: (sample, target) where target is class_index of the target class.
        """
        if self.is_zip:
            path, target = self.samples[index]
            end = time.time()
            samples = zip_loader(path)
            load_time = time.time() - end
#            print('load 4 images in a file time:{}'.format(load_time))
            if self.transform is not None:
                samples = [self.transform(sample) for sample in samples]
            if self.target_transform is not None:
                print("\n\nself.target_transform.....\n\n")
                target = self.target_transform(target)
            res = samples, target
#            print(res)
            return res
            

        if self.is_tar:
            path, target = self.samples[index]
            end = time.time()
            samples = tar_loader(path)
            load_time = time.time() - end
          #  print('load 4 images in a file time:{}'.format(load_time))
            if self.transform is not None:
                samples = [self.transform(sample) for sample in samples]
            if self.target_transform is not None:
                print("\n\nself.target_transform.....\n\n")
                target = self.target_transform(target)
            res = samples, target
#            print(res)
            return res
            

        if self.is_meng:
            path, target = self.samples[index]
            end = time.time()
            samples = meng_loader(path)
            load_time = time.time() - end
            print('load 4 images in a file time:{}'.format(load_time))
            if self.transform is not None:
                samples = [self.transform(sample) for sample in samples]
            if self.target_transform is not None:
                target = self.target_transform(target)
            res = samples, target
#            print(res)
            return res
        path, target = self.samples[index]
        end = time.time()
        sample = self.loader(path)
        load_time = time.time() - end
#        print("load one image time: {}".format(load_time))
        if self.transform is not None:
            end = time.time()
            sample = self.transform(sample)
            transform_time = time.time() - end
            print("    transform one image time: {}".format(transform_time))
        if self.target_transform is not None:
            target = self.target_transform(target)

        return sample, target

    def __len__(self) -> int:
        return len(self.samples)


    async def async_get_item(self, index: int) -> Tuple[Any, Any]:
        """
        Args:
            index (int): Index

        Returns:
            tuple: (sample, target) where target is class_index of the target class.
        """
        if self.is_zip:
            path, target = self.samples[index]
            end = time.time()
            samples = zip_loader(path)
            load_time = time.time() - end
#            print('load 4 images in a file time:{}'.format(load_time))
            if self.transform is not None:
                samples = [self.transform(sample) for sample in samples]
            if self.target_transform is not None:
                print("\n\nself.target_transform.....\n\n")
                target = self.target_transform(target)
            res = samples, target
#            print(res)
            return res
            

        if self.is_tar:
            path, target = self.samples[index]
            end = time.time()
            samples = await async_tar_loader(path)
            load_time = time.time() - end
          #  print('load 4 images in a file time:{}'.format(load_time))
            if self.transform is not None:
                samples = [self.transform(sample) for sample in samples]
            if self.target_transform is not None:
                print("\n\nself.target_transform.....\n\n")
                target = self.target_transform(target)
            res = samples, target
#            print(res)
            return res
            

        if self.is_meng:
            path, target = self.samples[index]
            end = time.time()
            samples = meng_loader(path)
            load_time = time.time() - end
            print('load 4 images in a file time:{}'.format(load_time))
            if self.transform is not None:
                samples = [self.transform(sample) for sample in samples]
            if self.target_transform is not None:
                target = self.target_transform(target)
            res = samples, target
#            print(res)
            return res
        path, target = self.samples[index]
        end = time.time()
        sample = await async_pil_loader(path)
        load_time = time.time() - end
#        print("load one image time: {}".format(load_time))
        if self.transform is not None:
            end = time.time()
            sample = self.transform(sample)
            transform_time = time.time() - end
            print("    transform one image time: {}".format(transform_time))
        if self.target_transform is not None:
            target = self.target_transform(target)

        return sample, target

    
IMG_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.ppm', '.bmp', '.pgm', '.tif', '.tiff', '.webp', '.pickle', '.zip', 'tar')


def pil_loader(path: str) -> Image.Image:
    # open path as file to avoid ResourceWarning (https://github.com/python-pillow/Pillow/issues/835)
    end = time.time()
    with open(path, 'rb') as f:
        f = f.read()
        f = io.BytesIO(f)
        io_read_time = time.time() - end
        end = time.time()
        img = Image.open(f)
        res = img.convert('RGB')
        pil_img_decode_time = time.time() - end
        print("    io_read_time: {}  pil_img_decode_time: {}".format(io_read_time, pil_img_decode_time))
        return res

 async def pil_loader(path: str) -> Image.Image:
    # open path as file to avoid ResourceWarning (https://github.com/python-pillow/Pillow/issues/835)
    end = time.time()
    async with aiofiles.open(path, 'rb') as f:
        f = await f.read()
        f = io.BytesIO(f)
        io_read_time = time.time() - end
        end = time.time()
        img = Image.open(f)
        res = img.convert('RGB')
        pil_img_decode_time = time.time() - end
        print("    io_read_time: {}  pil_img_decode_time: {}".format(io_read_time, pil_img_decode_time))
        return res
    
    
 
def meng_loader(path: str) -> [Image.Image]:
    with open(path, 'rb') as f:
        imgs = pickle.load(f)
        return imgs

def zip_loader(path: str) -> Image.Image:
    # open path as file to avoid ResourceWarning (https://github.com/python-pillow/Pillow/issues/835)
    imgs = []
    with ZipFile(path) as archive:
        for entry in archive.infolist():
            with archive.open(entry) as file:
                img = Image.open(file)
                imgs.append(img.convert('RGB'))
    return imgs


def tar_loader(path: str) -> Image.Image:
    # open path as file to avoid ResourceWarning (https://github.com/python-pillow/Pillow/issues/835)
    imgs = []
    end = time.time()
    with open(path, 'rb') as f:
        f = f.read()
        iobytes = io.BytesIO(f)
        tar_read_time = time.time() - end
        print("    tar_read_time: {}".format(tar_read_time))
        with tarfile.open(fileobj=iobytes) as archive:
            for entry in archive.getmembers():
                end = time.time()
                with archive.extractfile(entry) as file:
                    per_img_extract_tile = time.time() - end
                    end = time.time()
                    img = Image.open(file)
                    imgs.append(img.convert('RGB'))
                    pil_img_decode_time = time.time() - end
                    print("        per_img_extract_tile: {}  pil_img_decode_time: {}".format(per_img_extract_tile, pil_img_decode_time))
    return imgs


async def async_tar_loader(path: str) -> Image.Image:
    # open path as file to avoid ResourceWarning (https://github.com/python-pillow/Pillow/issues/835)
    imgs = []
    end = time.time()
    async with open(path, 'rb') as f:
        f = await f.read()
        iobytes = io.BytesIO(f)
        tar_read_time = time.time() - end
        print("    tar_read_time: {}".format(tar_read_time))
        with tarfile.open(fileobj=iobytes) as archive:
            for entry in archive.getmembers():
                end = time.time()
                with archive.extractfile(entry) as file:
                    per_img_extract_tile = time.time() - end
                    end = time.time()
                    img = Image.open(file)
                    imgs.append(img.convert('RGB'))
                    pil_img_decode_time = time.time() - end
                    print("        per_img_extract_tile: {}  pil_img_decode_time: {}".format(per_img_extract_tile, pil_img_decode_time))
    return imgs



def tar_loader(path: str) -> Image.Image:
    # open path as file to avoid ResourceWarning (https://github.com/python-pillow/Pillow/issues/835)
    imgs = []
    with tarfile.open(path) as archive:
        for entry in archive.getmembers():
            with archive.extractfile(entry) as file:
                img = Image.open(file)
                imgs.append(img.convert('RGB'))
    return imgs


# TODO: specify the return type
def accimage_loader(path: str) -> Any:
    import accimage
    try:
        return accimage.Image(path)
    except IOError:
        # Potentially a decoding problem, fall back to PIL.Image
        return pil_loader(path)


def default_loader(path: str) -> Any:
    from torchvision import get_image_backend
    if get_image_backend() == 'accimage':
        return accimage_loader(path)
    else:
        return pil_loader(path)


class ImageFolder(DatasetFolder):
    """A generic data loader where the images are arranged in this way: ::

        root/dog/xxx.png
        root/dog/xxy.png
        root/dog/[...]/xxz.png

        root/cat/123.png
        root/cat/nsdf3.png
        root/cat/[...]/asd932_.png

    Args:
        root (string): Root directory path.
        transform (callable, optional): A function/transform that  takes in an PIL image
            and returns a transformed version. E.g, ``transforms.RandomCrop``
        target_transform (callable, optional): A function/transform that takes in the
            target and transforms it.
        loader (callable, optional): A function to load an image given its path.
        is_valid_file (callable, optional): A function that takes path of an Image file
            and check if the file is a valid file (used to check of corrupt files)

     Attributes:
        classes (list): List of the class names sorted alphabetically.
        class_to_idx (dict): Dict with items (class_name, class_index).
        imgs (list): List of (image path, class_index) tuples
    """

    def __init__(
            self,
            root: str,
            transform: Optional[Callable] = None,
            target_transform: Optional[Callable] = None,
            loader: Callable[[str], Any] = default_loader,
            is_valid_file: Optional[Callable[[str], bool]] = None,
            is_meng: bool = False,
            is_zip: bool = False,
            is_tar: bool = False
    ):
        super(ImageFolder, self).__init__(root, loader, IMG_EXTENSIONS if is_valid_file is None else None,
                                          transform=transform,
                                          target_transform=target_transform,
                                          is_valid_file=is_valid_file)
        self.imgs = self.samples
        self.is_meng = is_meng
        self.is_zip = is_zip
        self.is_tar = is_tar

        if(is_meng):
            print("meng's image folder!")
        if(is_zip):
            print("using zip format!")
        if(is_tar):
            print("using tar format!")

"""
class MengImageFolder(DatasetFolder):
    def __init__(
            self,
            root: str,
            transform: Optional[Callable] = None,
            target_transform: Optional[Callable] = None,
            loader: Callable[[str], Any] = default_loader,
            is_valid_file: Optional[Callable[[str], bool]] = None,
    ):
        super(MengImageFolder, self).__init__(root, loader, IMG_EXTENSIONS if is_valid_file is None else None,
                                          transform=transform,
                                          target_transform=target_transform,
                                          is_valid_file=is_valid_file)
        self.imgs = self.samples
"""

"""
    def __getitem__(self, index: int) -> Tuple[Any, Any]:
        path, target = self.samples[index]
        samples = mengloader(path)
        if self.transform is not None:
            samples = [self.transform(sample) for sample in samples]
        if self.target_transform is not None:
            target = self.target_transform(target)
        res = samples, target
        print(res)
        return res

"""
