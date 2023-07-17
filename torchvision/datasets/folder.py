from .vision import VisionDataset

from PIL import Image

import io
import os
import os.path
from typing import Any, Callable, cast, Dict, List, Optional, Tuple

import minio

import io


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

# meng: get metadata for mytar files, so that we know the classes and index of images.
def get_metadata_mytar(
    directory: str,
    group_size: int
):
    directory = os.path.expanduser(directory)
    metadata_path = os.path.join(directory, "metadata.txt")
    metadata = []
    classes = []
    with open(metadata_path, 'r') as reader:
        # first get all classes
        class_count = int(reader.readline().strip())
        for _ in range(class_count):
            class_name = reader.readline().strip()
            classes.append(class_name)
        classes.sort()
        class_to_idx = {cls_name: i for i, cls_name in enumerate(classes)} 
        print(class_to_idx)
        # then get all groups metadata
        while reader:
            groupname = reader.readline().strip().split(',')[0]
            if(groupname == ''):
                break
            group = []
            for i in range(group_size):
                values = reader.readline().strip().split(',')
                idx = values[0]
                img_class = values[1]
                start = int(values[2])
                img_size = int(values[3])
                img_class_idx = class_to_idx[img_class]
                group.append({'idx':idx, 'img_class':img_class, 'img_class_idx':img_class_idx, 'start':start, 'img_size':img_size})
            metadata.append({'groupname':groupname, 'metadata':group})
    print(class_to_idx)
    return metadata



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
        if hasattr(self, 'use_file_group') and self.use_file_group:
            self.metadata = get_metadata_mytar(root, self.group_size)
        else:
            classes, class_to_idx = self._find_classes(self.root)
            samples = self.make_dataset(self.root, class_to_idx, extensions, is_valid_file)
            if len(samples) == 0:
                msg = "Found 0 files in subfolders of: {}\n".format(self.root)
                if extensions is not None:
                    msg += "Supported extensions are: {}".format(",".join(extensions))
                raise RuntimeError(msg)
            
            self.classes = classes
            self.class_to_idx = class_to_idx
            self.samples = samples
            self.targets = [s[1] for s in samples]

        self.loader = loader
        self.extensions = extensions

        

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
        if self.use_file_group:
            path = self.root + '/' + self.metadata[index]['groupname']
            group_metadata = self.metadata[index]['metadata']
            samples, targets = mytar_loader(path, group_metadata)
            if self.transform is not None:
                samples = [self.transform(sample) for sample in samples]
            if self.target_transform is not None:
                # print("\n\nself.target_transform.....\n\n")
                targets = [self.target_transform(target) for target in targets]
            res = samples, targets
            return res

        path, target = self.samples[index]
        sample = self.loader(path, self.cache)
        if self.transform is not None:
            sample = self.transform(sample)
        if self.target_transform is not None:
            target = self.target_transform(target)

        return sample, target

    def __len__(self) -> int:
        if self.use_file_group:
            return len(self.metadata)
        else:
            return len(self.samples)


IMG_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.ppm', '.bmp', '.pgm', '.tif', '.tiff', '.webp',
                    '.pickle', '.zip', 'tar', 'mytar')


def pil_loader(path: str, cache: minio.PyCache) -> Image.Image:
    # open path as file to avoid ResourceWarning (https://github.com/python-pillow/Pillow/issues/835)
    with open(path, 'rb') as f:
        f = f.read()
        f = io.BytesIO(f)
        img = Image.open(f)
        return img.convert('RGB')


def mytar_loader(path: str, group_metadata):
    imgs = []
    targets = []
    with open(path, 'rb') as f:
        f = f.read()
        for img_info in group_metadata:
                img_start = img_info['start']
                img_end = img_start + img_info['img_size']
                img_class_idx = img_info['img_class_idx']

                # print('img_class_idx:{}'.format(img_class_idx))
                img_data = f[img_start:img_end]
                iobytes = io.BytesIO(img_data)

                img = Image.open(iobytes)
                imgs.append(img.convert('RGB'))
                targets.append(img_class_idx)
    return imgs, targets


# TODO: specify the return type
def accimage_loader(path: str, cache: minio.PyCache) -> Any:
    import accimage
    try:
        return accimage.Image(path)
    except IOError:
        # Potentially a decoding problem, fall back to PIL.Image
        return pil_loader(path, cache)


def default_loader(path: str, cache: minio.PyCache) -> Any:
    from torchvision import get_image_backend
    if get_image_backend() == 'accimage':
        return accimage_loader(path)
    else:
        return pil_loader(path, cache)


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
            cache: minio.PyCache = None,
            loader: Callable[[str], Any] = default_loader,
            is_valid_file: Optional[Callable[[str], bool]] = None,
            use_file_group: bool = False,
            group_size: int = 1,
    ):
        self.use_file_group = use_file_group
        self.group_size = group_size
        super(ImageFolder, self).__init__(root, loader, IMG_EXTENSIONS if is_valid_file is None else None,
                                          transform=transform,
                                          target_transform=target_transform,
                                          is_valid_file=is_valid_file)
        if not self.use_file_group:
            self.imgs = self.samples
        self.cache = cache

        if self.cache != None:
            print("Using MinIO cache with size {} KB.".format(self.cache.get_size() / 1024))
        else:
            print("NOT using MinIO cache.")
