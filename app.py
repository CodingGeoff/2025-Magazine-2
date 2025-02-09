import os
import random
import re
import string
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for
import pyperclip
import hashlib
from urllib.parse import quote  # 导入 URL 编码工具
from PyPDF2 import PdfReader, PdfWriter
import math

app = Flask(__name__)
shard = "§§§§"
UPLOAD_FOLDER = 'static/uploads'
HASH_FILE = 'static/file_hashes.txt'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

if not os.path.exists(HASH_FILE):
    open(HASH_FILE, 'w').close()

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 更多有意义的单词用于生成正确密钥
MEANINGFUL_WORDS = [
    "sunshine", "rainbow", "ocean", "mountain", "forest",
    "star", "moon", "flower", "butterfly", "cloud",
    "river", "island", "valley", "desert", "canyon",
    "meadow", "glacier", "volcano", "lake", "waterfall",
    "wind", "fire", "earth", "air", "snow",
    "ice", "mist", "dew", "frost", "hail",
    "thunder", "lightning", "storm", "hurricane", "tornado",
    "drizzle", "shower", "blizzard", "fog", "smog",
    "planet", "comet", "asteroid", "galaxy", "nebula",
    "universe", "constellation", "meteor", "meteorite",
    "tree", "leaf", "branch", "root", "bark",
    "grass", "weed", "vine", "fern", "moss",
    "bamboo", "pinecone", "acorn", "seed", "bud",
    "blossom", "lion", "tiger", "bear", "wolf",
    "fox", "deer", "rabbit", "squirrel", "bird",
    "eagle", "dove", "sparrow", "owl", "fish",
    "shark", "whale", "dolphin", "turtle", "snake",
    "lizard", "frog", "toad", "bee", "ant",
    "spider", "worm", "love", "joy", "happiness",
    "peace", "hope", "faith", "courage", "confidence",
    "pride", "excitement", "enthusiasm", "contentment", "gratitude",
    "kindness", "compassion", "empathy", "friendship", "loyalty",
    "trust", "sadness", "grief", "anger", "hate",
    "fear", "anxiety", "worry", "stress", "loneliness",
    "envy", "jealousy", "regret", "guilt", "shame",
    "wisdom", "intelligence", "creativity", "perseverance", "patience",
    "tolerance", "generosity", "honesty", "integrity", "humility",
    "bravery", "selflessness", "responsibility", "determination",
    "sight", "sound", "smell", "taste", "touch",
    "vision", "hearing", "aroma", "flavor", "texture",
    "pain", "pleasure", "warmth", "cold", "light",
    "dark", "soul", "spirit", "god", "goddess",
    "angel", "demon", "heaven", "hell", "karma",
    "reincarnation", "meditation", "prayer", "shrine", "temple",
    "church", "mosque", "synagogue", "truth", "beauty",
    "good", "evil", "justice", "freedom", "equality",
    "virtue", "vice", "logic", "reason", "ethics",
    "morality", "aesthetics", "ontology", "epistemology",
    "time", "space", "moment", "hour", "day",
    "week", "month", "year", "decade", "century",
    "millennium", "past", "present", "future", "distance",
    "height", "width", "depth", "length", "area",
    "volume", "red", "blue", "green", "yellow",
    "black", "white", "purple", "pink", "orange",
    "brown", "gray", "silver", "gold", "bronze",
    "turquoise", "violet", "heart", "cross", "star of David",
    "crescent moon", "yin - yang", "peace sign", "dove", "olive branch",
    "rose", "lotus", "anchor", "ladder", "idea",
    "thought", "concept", "theory", "knowledge", "information",
    "power", "energy", "art", "culture", "history",
    "memory", "dream", "fantasy", "reality", "illusion"
]

# 定义文件图标类名和颜色的函数
def get_file_icon_class(file):
    ext = file.split('.')[-1].lower()
    icon_classes = {
        'pdf': 'fa-solid fa-file-pdf',
        'docx': 'fa-solid fa-file-word',
        'xlsx': 'fa-solid fa-file-excel',
        'pptx': 'fa-solid fa-file-powerpoint'
    }
    return icon_classes.get(ext, 'fa-solid fa-file')

def get_file_icon_color(file):
    ext = file.split('.')[-1].lower()
    icon_colors = {
        'pdf': '#e74c3c',
        'docx': '#2ecc71',
        'xlsx': '#f1c40f',
        'pptx': '#3498db'
    }
    return icon_colors.get(ext, '#95a5a6')

# 将函数注册为 Jinja2 全局函数
app.jinja_env.globals.update(get_file_icon_class=get_file_icon_class)
app.jinja_env.globals.update(get_file_icon_color=get_file_icon_color)

def generate_random_string(length):
    """生成指定长度的不可读随机字符串"""
    letters_and_digits = string.ascii_letters + string.digits
    return ''.join(random.choice(letters_and_digits) for i in range(length))

def generate_keys():
    now = datetime.now()
    seed = f"{now.year}{now.month}{now.day}{now.hour}{now.minute}{now.second}"
    random.seed(seed)
    correct_key = random.choice(MEANINGFUL_WORDS)
    wrong_keys = [generate_random_string(random.randint(5, 9)) for _ in range(9)]
    all_keys = [correct_key] + wrong_keys
    random.shuffle(all_keys)
    return all_keys, correct_key

def calculate_file_hash(file):
    """计算文件的哈希值"""
    hash_object = hashlib.sha256()
    for chunk in iter(lambda: file.read(4096), b""):
        hash_object.update(chunk)
    file.seek(0)  # 将文件指针重置到文件开头
    return hash_object.hexdigest()

def check_file_hash_exists(file_hash):
    """检查哈希值是否已存在"""
    with open(HASH_FILE, 'r') as f:
        hashes = f.read().splitlines()
    return file_hash in hashes

def add_file_hash(file_hash):
    """将哈希值添加到文件中"""
    with open(HASH_FILE, 'a') as f:
        f.write(file_hash + '\n')

# 对文件进行分组
def generate_file_groups(uploaded_files):
    """改进的文件分组逻辑"""
    file_groups = {}
    for filename in uploaded_files:
        # 移除扩展名
        base_name = os.path.splitext(filename)[0]

        # 处理分片标识
        if shard in base_name:
            group_name = base_name.split(shard)[0]
        else:
            group_name = base_name

        # 清理特殊后缀
        group_name = re.sub(r'_freemagazines_top.*', '', group_name)
        group_name = group_name.replace('_', ' ')

        if group_name not in file_groups:
            file_groups[group_name] = []
        file_groups[group_name].append(filename)

    # 自然排序算法
    for group in file_groups.values():
        group.sort(key=lambda x: [
            int(s) if s.isdigit() else s.lower()
            for s in re.split('([0-9]+)', x)
        ])

    return file_groups

def split_pdf(input_pdf_path, output_folder):
    # 检查输入的PDF文件是否存在
    if not os.path.exists(input_pdf_path):
        print(f"输入的PDF文件 {input_pdf_path} 不存在。")
        return

    # 获取PDF文件的大小（单位：MB）
    file_size = os.path.getsize(input_pdf_path) / (1024 * 1024)

    # 检查输出文件夹是否存在，如果不存在则创建
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 如果文件大小小于等于80MB，直接复制到输出文件夹
    if file_size <= 80:
        import shutil
        shutil.copy2(input_pdf_path, output_folder)
        print(f"文件大小小于等于80MB，已直接复制到 {output_folder}。")
        return

    # 读取PDF文件
    reader = PdfReader(input_pdf_path)
    num_pages = len(reader.pages)

    # 计算需要分割的份数
    num_splits = math.ceil(file_size / 100)

    # 计算每份的大致页数
    pages_per_split = math.ceil(num_pages / num_splits)

    # 获取原文件名（不包含扩展名）
    file_name = os.path.splitext(os.path.basename(input_pdf_path))[0]

    # 分割PDF文件
    for i in range(num_splits):
        writer = PdfWriter()
        start_page = i * pages_per_split
        end_page = min((i + 1) * pages_per_split, num_pages)

        # 添加页面到新的PDF文件
        for page_num in range(start_page, end_page):
            writer.add_page(reader.pages[page_num])

        # 生成输出文件名
        output_file_name = f"{file_name}{shard}{i + 1}.pdf"
        output_file_path = os.path.join(output_folder, output_file_name)

        # 保存新的PDF文件
        with open(output_file_path, "wb") as output_file:
            writer.write(output_file)

        print(f"已保存分割后的文件: {output_file_path}")


@app.route('/', methods=['GET', 'POST'])
def index():
    # 获取上传文件夹中的所有文件列表并复制到剪贴板
    uploaded_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if f.endswith('.pdf')]

    formatted_files = [f"'{file}'" for file in uploaded_files]
    files_list_str = f"[{', '.join(formatted_files)}]"
    print("Uploaded Files:", files_list_str)
    pyperclip.copy("const pdfFiles =" + files_list_str + ";")
    error = ''
    keys, correct_key = generate_keys()
    # 生成文件分组
    file_groups = generate_file_groups(uploaded_files)

    if request.method == 'POST':
        file = request.files['file']
        selected_key = request.form.get('selectedKey')
        if selected_key not in MEANINGFUL_WORDS:
            error = 'Invalid key selected.'
        elif file:
            # 计算文件的哈希值
            file_hash = calculate_file_hash(file.stream)
            if check_file_hash_exists(file_hash):
                print(f"文件 {file.filename} 已存在。")
                error = "File already exists."
            else:
                # 获取原始文件名
                original_filename = file.filename
                # 去掉 _freemagazines_top 及其后面的内容
                if '_freemagazines_top' in original_filename:
                    new_filename = original_filename.split('_freemagazines_top')[0]
                    if not new_filename.endswith('.pdf'):
                        new_filename += '.pdf'
                else:
                    new_filename = original_filename
                # 将文件名中的 _ 替换为空格
                new_filename = new_filename.replace('_', ' ')
                # 确保文件名是唯一的，避免覆盖
                base_name, ext = os.path.splitext(new_filename)
                counter = 1
                while os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], new_filename)):
                    new_filename = f"{base_name} ({counter}){ext}"
                    counter += 1
                # 保存文件到指定目录
                temp_file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
                # temp_file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_' + new_filename)
                file.save(temp_file_path)

                # 检查文件大小，如果是 PDF 且大于 100MB 则进行分割
                file_size = os.path.getsize(temp_file_path) / (1024 * 1024)
                if ext.lower() == '.pdf' and file_size > 100:
                    split_pdf(temp_file_path, app.config['UPLOAD_FOLDER'])
                    os.remove(temp_file_path)  # 删除临时文件
                else:
                    final_file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
                    os.rename(temp_file_path, final_file_path)

                # 将哈希值添加到文件中
                add_file_hash(file_hash)
                return redirect(url_for('index'))

    return render_template('index.html', error=error, uploaded_files=uploaded_files, keys=keys, file_groups=file_groups, quote=quote)

if __name__ == '__main__':
    app.run(debug=True)