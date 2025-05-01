import os
import shutil
import imagehash
import cv2
import numpy as np
from PIL import Image
from collections import defaultdict
from skimage.metrics import structural_similarity as ssim


def create_or_clean_dir(base_dir, dir_name, class_name):
    """创建或清空指定的目录，并打印状态信息"""
    dir_path = os.path.join(base_dir, dir_name)
    class_path = os.path.join(dir_path, class_name)
    if os.path.exists(dir_path):
        os.makedirs(class_path)
        print(f"{class_path} 创建成功。")
    else:
        os.makedirs(class_path)
    return class_path


def print_stage_info(stage, pairs_count=None):
    """打印阶段信息"""
    if pairs_count is not None:
        print(f"{stage}阶段完成，找到 {pairs_count} 组可能相似的图片。")
    else:
        print(f"{stage}阶段完成。")


def calculate_color_histogram(image):
    """计算图像的颜色直方图并进行归一化。"""
    hist = cv2.calcHist([image], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
    cv2.normalize(hist, hist)
    return hist.flatten()


def resize_image(image, size):
    """将图像调整为指定的尺寸。"""
    return cv2.resize(image, size, interpolation=cv2.INTER_AREA)


def calculate_ssim(image_path1, image_path2):
    """计算两幅图像的结构相似度指数SSIM"""
    image1 = cv2.imread(image_path1, cv2.IMREAD_COLOR)
    image2 = cv2.imread(image_path2, cv2.IMREAD_COLOR)
    gray1 = cv2.cvtColor(image1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(image2, cv2.COLOR_BGR2GRAY)
    ssim_score = ssim(gray1, gray2, multichannel=True)
    return ssim_score


def calculate_sharpness(image):
    """使用拉普拉斯方差计算图像的锐利度。"""
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray_image, cv2.CV_64F).var()
    return laplacian_var


def calculate_noise(image):
    """计算图像的噪声水平，使用均方差（MSE）。"""
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    mean = np.mean(gray_image)
    mse = np.mean((gray_image - mean) ** 2)
    return mse


def read_image_with_pillow(image_path):
    """使用 Pillow 读取图像并转换为 OpenCV 格式。"""
    # 使用 Pillow 读取图像
    image = Image.open(image_path)
    # 确保图像是 RGB 格式
    image = image.convert('RGB')
    # 将图像转换为 NumPy 数组
    image = np.array(image)
    # 将 RGB 格式转换为 OpenCV 使用的 BGR 格式
    image = image[:, :, ::-1]
    return image


def get_file_info(file_path):
    """获取文件的大小、修改时间和创建时间。"""
    file_size = os.path.getsize(file_path)
    modification_time = os.path.getmtime(file_path)
    creation_time = os.path.getctime(file_path)
    return file_size, modification_time, creation_time


def perceptual_hash_filter(root, files):
    """使用 pHash 初步筛选相似图片"""
    print()
    print("-" * 20, f"开始使用 pHash 初步筛选相似图片，路径：{root}")
    hash_dict = {}
    for file in files:
        if not file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
            # 只处理图片文件
            continue
        src_path = os.path.join(root, file)
        img = Image.open(src_path)

        phash = imagehash.phash(img)
        hash_dict[file] = phash

    threshold = 0.5
    similar_pairs = []
    for i, (path1, hash1) in enumerate(hash_dict.items()):
        for j, (path2, hash2) in enumerate(hash_dict.items()):
            # 确保只进行必要的比较，避免重复
            if i < j and hash1 - hash2 < threshold:
                file1_path = os.path.join(root, path1)
                file2_path = os.path.join(root, path2)
                print(f"标记：{path1} 和 {path2} 的感知哈希相似")

                similar_pairs.append((file1_path, file2_path))
    print_stage_info("感知哈希筛选", len(similar_pairs))
    return similar_pairs


def compare_images_ssim(image_pairs, root, ssim_threshold=0.80, hist_threshold=0.80):
    """通过 SSIM 和颜色直方图比较两张图像是否重复。

    Args:
        image_pairs:
        root:
        ssim_threshold (float): 判断图像是否重复的 SSIM 阈值，默认为 0.95。
        hist_threshold (float): 判断图像是否重复的颜色直方图相似度阈值，默认为 0.90。

    Returns:
        bool: 如果两张图像的 SSIM 和颜色直方图相似度都大于等于阈值，则返回 True；否则返回 False。
    """
    print()
    print("-" * 20, f"开始使用 SSIM 进一步筛选相似图片, 路径：{root}")
    similar_images = []
    for image1_path, image2_path in image_pairs:
        image1 = read_image_with_pillow(image1_path)
        image2 = read_image_with_pillow(image2_path)

        if image1 is None or image2 is None:
            raise ValueError("有一张图像无法加载。请检查文件路径。")

            # 将图像调整为相同的尺寸（使用第一张图像的尺寸）
        size = (image1.shape[1], image1.shape[0])
        image2_resized = resize_image(image2, size)
        # 将图像转换为灰度图像
        gray_image1 = cv2.cvtColor(image1, cv2.COLOR_BGR2GRAY)
        gray_image2 = cv2.cvtColor(image2_resized, cv2.COLOR_BGR2GRAY)

        # 计算 SSIM
        ssim_score, _ = ssim(gray_image1, gray_image2, full=True)

        # 计算颜色直方图相似度
        hist1 = calculate_color_histogram(image1)
        hist2 = calculate_color_histogram(image2)
        hist_similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)

        # 判断是否重复
        if ssim_score >= ssim_threshold and hist_similarity >= hist_threshold:
            base_name1 = os.path.basename(image1_path)
            base_name2 = os.path.basename(image2_path)
            print(
                f"标记：{base_name1} 和 {base_name2} 相似，"
                f"SSIM 值：{ssim_score}，颜色直方图相似度：{hist_similarity}")

            similar_images.append((image1_path, image2_path))

    print_stage_info("SSIM 筛选", len(similar_images))
    return similar_images


def pixel_comparison(image_pairs):
    """像素级比较确认完全相同图片，并打印结果"""
    identical_images = []
    for pair in image_pairs:
        img1 = Image.open(pair[0])
        img2 = Image.open(pair[1])
        if img1.size == img2.size:
            arr1 = np.array(img1)
            arr2 = np.array(img2)
            if np.array_equal(arr1, arr2):
                identical_images.append(pair)
    print_stage_info("像素比较", len(identical_images))
    return identical_images


def merge_pic_with_common_elements(similar_pairs):
    """
    过滤重复2张以上的图片
    :param similar_pairs:
    :return:
    """

    # 使用字典按元素分组
    grouped_tuples = defaultdict(list)
    for tup in similar_pairs:
        for elem in tup:
            grouped_tuples[elem].append(tup)

    # 合并至少有一个元素共享的元组
    merged_tuples = []
    unique_elements = set()
    for group in grouped_tuples.values():
        # 只考虑至少有两个元组共享至少一个元素的情况
        if len(group) > 1:
            combined_tup = set().union(*group)  # 合并所有元组的元素并去重
            # 确保合并后的元组中不包含已经在其他合并元组中出现过的元素
            if not any(combined_tup.intersection(set(t)) for t in merged_tuples):
                merged_tuples.append(tuple(sorted(combined_tup)))  # 添加排序后的元组到结果列表
                unique_elements.update(combined_tup)  # 更新已处理的元素集合

    # 添加未参与合并的独立元组
    independent_tuples = [tup for tup in similar_pairs if not any(elem in unique_elements for elem in tup)]

    return independent_tuples + merged_tuples


def choose_image_to_folder(file_pairs, root, folder_name):
    """将文件移动到指定文件夹，并打印操作信息"""

    for i, pairs in enumerate(file_pairs):

        images_info = []  # 存储每张图片的路径、锐利度、噪声水平、综合评分
        for src_path in pairs:
            image_path = read_image_with_pillow(src_path)
            if image_path is None:
                raise ValueError(f"图像'{src_path}'无法加载。请检查文件路径。")
            base_name = os.path.basename(src_path)

            sharpness = calculate_sharpness(image_path)
            noise = calculate_noise(image_path)

            score = sharpness / noise if noise != 0 else float('inf') if sharpness != 0 else 0
            file_info = get_file_info(src_path)
            images_info.append((src_path, score, file_info))
            print(f"{base_name} 的锐利度：{sharpness}, 噪声水平：{noise}, 综合评分：{score}, 图像信息：{file_info}")
        images_info = sorted(images_info, key=lambda x: (x[1], x[2][0], -x[2][1], -x[2][2]), reverse=True)
        print(f"\n第 {i + 1} 组图像比较完成。")

        dst_path = create_or_clean_dir(root, folder_name, f"第{i + 1}组")
        for j, item in enumerate(images_info):
            if j == 0:
                shutil.copy(item[0], dst_path)
            else:
                base_name = os.path.basename(item[0])
                file_name, ext = os.path.splitext(base_name)
                move_name = f"MOVE_{file_name}{ext.lower()}"
                move_path = os.path.join(dst_path, move_name)

                shutil.move(item[0], move_path)
                print(f"移动重复图片: {move_name} -> {move_path}")


def main(dst_root):
    print(dst_root)
    folder_name = "Duplicates"
    for root, dirs, files in os.walk(dst_root):
        if files:
            duplicates_path = os.path.join(root, folder_name)
            if os.path.exists(duplicates_path):
                print(f"开始清空目标目录： {duplicates_path}")
                shutil.rmtree(duplicates_path)
            phash_similar_pairs = perceptual_hash_filter(root, files)
            if phash_similar_pairs:

                ssim_similar_pairs = compare_images_ssim(phash_similar_pairs, root)
                similar_pairs = merge_pic_with_common_elements(ssim_similar_pairs)
                choose_image_to_folder(similar_pairs, root, folder_name)


if __name__ == "__main__":
    dest_root = 'D:\\Always\\Desktop\\Pictures'
    # dest_root = 'D:\\Pictures1'
    main(dest_root)
