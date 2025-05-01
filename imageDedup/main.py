from handle_image_files import main as image_main

from image_duplicates import main as duplicates

source_root = 'D:\\Home\\Desktop\\Pic'  # 源目录路径
dest_root = 'D:\\Home\\Desktop\\Pictures'  # 目标目录路径

# 从源目录 Copy 到目标目录，并完成重命名， 支持 视频、图片
image_main(source_root, dest_root)

# 在目标目录检测重复图片，优质图片保留到源目录，其他图片剪切到 Duplicates 目录
duplicates(dest_root)
