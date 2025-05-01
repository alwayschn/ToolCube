import os
import shutil
import random
import hashlib
import re
from datetime import datetime
from PIL import Image, ExifTags
import image_duplicates


def is_all_chinese(filename):
    """检查文件名是否全部由中文字符组成"""
    # print(filename)

    return bool(re.fullmatch(r'^[\u4e00-\u9fa5]+$', filename))


def generate_random_code():
    """生成6位随机数字"""
    return ''.join(str(random.randint(0, 9)) for _ in range(6))


def get_modified_date(file_path):
    """获取文件的修改日期，格式化为 YYYYMMDD """
    return datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y%m%d')


def remove_duplicate_extension(file_path):
    # 分割文件路径和基础文件名
    base_name = os.path.basename(file_path)
    path_no_ext = os.path.dirname(file_path)

    # 再次分割文件名以查找所有"."，然后重新组合除了最后一个"."之后的部分
    split_name = base_name.rsplit('.', 1)
    if len(split_name) > 1:  # 确保有扩展名
        # 保留文件名部分和最后一个扩展名
        clean_name = split_name[0] + "." + split_name[1]
    else:
        # 如果没有找到"."，说明没有扩展名或只有一个点，直接使用base_name
        clean_name = base_name

    # 重新组合路径和清理后的文件名
    corrected_path = os.path.join(path_no_ext, clean_name)
    return corrected_path


def check_image_ratio(img_path, ext):
    """检查图片尺寸比例，返回比例类型或None"""

    img_path = remove_duplicate_extension(img_path)
    try:
        user_comment = ""
        with Image.open(img_path) as img:
            # 解析EXIF数据
            if ext.lower() not in ('.mp4', '.avi', '.mov', '.mkv', '.ico', '.gif'):
                exif_data = img._getexif()
                if exif_data is not None:
                    # 将TAGS映射为人可读的标签
                    for tag_id, value in exif_data.items():
                        tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                        if tag_name == 'UserComment':
                            if isinstance(value, bytes):
                                value = value.decode('utf-8')
                            user_comment = value

                            # user_comment = value
            width, height = img.size
            ratio = width / height
            if ratio == 1 and ext.lower() != ".png":
                return 'Avatar'
            # elif (width >= 1920 and height >= 1080) or (height >= 1920 and width >= 1080):  # 简单判断是否适合做壁纸
            elif ((width / height) >= 1.5 or (height / width) >= 1.5) and ext.lower() != ".png":
                return 'Wallpaper'
            elif "Screenshot" in user_comment:
                return 'Screenshot'
    except IOError:
        pass
    return None


def rename_file(base_dir, src_path, file_type):
    """根据规则重命名并移动文件"""
    base_name = os.path.basename(src_path)
    name, ext = os.path.splitext(base_name)
    modified_date = get_modified_date(src_path)
    rand_code = generate_random_code()

    new_name = f"{file_type}_{modified_date}_{rand_code}{ext.lower()}"

    dir_path = os.path.dirname(src_path)
    new_path = os.path.join(dir_path, new_name)
    try:
        # 尝试执行重命名操作
        os.rename(src_path, new_path)
        src_relative_path = src_path.replace(base_dir, '')
        new_relative_path = new_path.replace(base_dir, '')
        print(f"文件已成功从 '{src_relative_path}' 重命名为 '{new_relative_path}'。")
        if ext.lower() in ('.mp4', '.avi', '.mov', '.mkv'):
            videos_dir = os.path.join(base_dir, 'Videos')
            os.makedirs(videos_dir, exist_ok=True)

            videos_path = os.path.join(videos_dir, new_name)
            shutil.move(new_path, videos_path)
            print(f"移动视频文件: {src_relative_path} --> {videos_path}")

    except FileNotFoundError:
        print(f"错误：原始文件或目录 '{src_path}' 未找到。")
    except FileExistsError:
        print(f"错误：目标文件或目录 '{new_path}' 已经存在。")
    except Exception as e:
        # 捕获其他所有可能的异常，如权限问题等
        print(f"重命名过程中发生错误：{e}")


def handle_files(dest_dir):
    print(dest_dir)
    """处理源目录下的所有文件"""
    pattern = r'^(IMG_|Wallpaper_|VID_|Avatar_|Screenshot_)\d{8}_\d{6}\.[a-z0-9]+$'
    for root, dirs, files in os.walk(dest_dir):
        for file in files:
            src_path = os.path.join(root, file)
            base_name = os.path.basename(src_path)
            file_name, ext = os.path.splitext(base_name)

            # 判断文件类型和重命名规则
            # 如果是全中文名称，则跳过重命名
            if is_all_chinese(file_name):
                print("跳过中文名称文件", base_name)
                continue

            file_type = None

            if re.match(pattern, base_name):
                # 文件名已符合规定格式，无需重命名
                print("跳过符合规则文件", base_name)
                if ext.lower() in ('.mp4', '.avi', '.mov', '.mkv'):
                    videos_dir = os.path.join(root, 'Videos')
                    os.makedirs(videos_dir, exist_ok=True)

                    videos_path = os.path.join(videos_dir, base_name)
                    shutil.move(src_path, videos_path)
                    print(f"移动视频文件: {src_path} --> {videos_path}")
                continue  # 跳过已符合规则的文件
            if ext.lower() in ('.mp4', '.avi', '.mov', '.mkv'):  # 视频文件后缀示例
                file_type = 'VID'
            elif ext.lower() in ('.ico', '.icon'):
                file_type = 'ICO'
            elif 'Screenshot' in base_name or check_image_ratio(src_path, ext) == 'Screenshot':
                file_type = 'Screenshot'
            elif check_image_ratio(src_path, ext) == 'Avatar':
                file_type = 'Avatar'
            elif check_image_ratio(src_path, ext) == 'Wallpaper':
                file_type = 'Wallpaper'
            else:
                file_type = 'IMG'
            # 重命名并移动文件
            if file_type:
                rename_file(dest_dir, src_path, file_type)


def compute_image_hash(image_path):
    """计算图片的MD5哈希值"""
    with open(image_path, 'rb') as f:
        image_data = f.read()
        return hashlib.md5(image_data).hexdigest()


def detect_duplicates_by_hash(dst_root):
    """基于哈希值检测并处理重复图片"""
    hashes = {}
    duplicates = []
    for root, dirs, files in os.walk(dst_root):
        for file in files:
            if not file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                # 只处理图片文件
                continue

            img_path = os.path.join(root, file)
            img_hash = compute_image_hash(img_path)

            if img_hash not in hashes:
                # 第一次遇到此哈希的图片，记录下来
                hashes[img_hash] = img_path
            else:
                # 已经有相同哈希的图片，视为重复，移动到Duplicates文件夹
                original_path = hashes[img_hash]
                duplicates_dir = os.path.join(root, 'Duplicates')
                os.makedirs(duplicates_dir, exist_ok=True)

                # 为了避免覆盖，可以给文件名添加一个随机后缀或序号
                duplicate_filename = f"{os.path.splitext(file)[0]}_duplicate_{generate_random_code()}{os.path.splitext(file)[1]}"
                duplicate_path = os.path.join(duplicates_dir, duplicate_filename)
                duplicates.append((img_path, duplicate_path))
                shutil.move(img_path, duplicate_path)
                print(f"移动重复图片: {file} -> {duplicate_path}")

    if duplicates:
        print("重复图片处理完成。")
    else:
        print("未找到重复图片。")


def main(src_dir, dest_dir):
    print("数源目录：", src_dir)
    print("目标目录：", dest_dir)
    # 检查目标目录是否存在，如果存在则清空
    if os.path.exists(dest_dir):
        print("开始清空目标目录...")
        shutil.rmtree(dest_dir)
    # 重新创建目标目录
    os.makedirs(dest_dir)

    print(f"开始 Copy 文件。 {src_dir} --> {dest_dir}")
    # 将源目录文件 copy 到目标目录，维持源目录结构
    shutil.copytree(src_dir, dest_dir, dirs_exist_ok=True)

    # 将目标目录的文件重命名
    if os.listdir(dest_dir):
        print(f"文件 Copy 成功！{os.listdir(dest_dir)}")
        print("开始对目录下的文件进行重命名...")
        handle_files(dest_dir)
    else:
        print("文件 Copy 失败，路径：", dest_dir)


if __name__ == "__main__":
    source_root = 'D:\\Always\\Desktop\\Pic'  # 源目录路径
    dest_root = 'D:\\Always\\Desktop\\Pictures'  # 目标目录路径
    main(source_root, dest_root)
    # 在主处理流程完成后调用此函数检测重复图片
    # detect_duplicates_by_hash(dest_root)
