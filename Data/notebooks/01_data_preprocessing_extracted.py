# Tắt các cảnh báo không cần thiết
import warnings
warnings.filterwarnings("ignore")

# Xử lý biểu thức chính quy
import re

# Thư viện xử lý dữ liệu
import numpy as np
import pandas as pd
from pathlib import Path

# Thư viện trực quan hóa
import matplotlib.pyplot as plt
import seaborn as sns

# Hiển thị đầy đủ các cột
pd.set_option("display.max_columns", None)
pd.set_option("display.max_colwidth", None)

# Thiết lập giao diện biểu đồ
plt.style.use("ggplot")

# ----------------------------------------

# Đường dẫn đến dữ liệu gốc
DATA_PATH = Path("../raw/house_price.csv")

# Đọc dữ liệu
df = pd.read_csv(DATA_PATH)


# ----------------------------------------

print(f"Số dòng: {df.shape[0]:,}")
print(f"Số cột : {df.shape[1]}")

# Hiển thị 5 dòng đầu tiên
df.head()

# ----------------------------------------

pd.DataFrame({
    "Tên thuộc tính": df.columns
})

# ----------------------------------------

# Thông tin tổng quan của bộ dữ liệu
df.info()

# ----------------------------------------

# Thống kê số lượng từng kiểu dữ liệu
df.dtypes.value_counts()

# ----------------------------------------

# Thống kê số lượng và tỷ lệ giá trị thiếu
missing = pd.DataFrame({
    "Số lượng thiếu": df.isnull().sum(),
    "Tỷ lệ (%)": (df.isnull().mean() * 100).round(2)
})

missing = missing[missing["Số lượng thiếu"] > 0]

missing.sort_values(
    by="Tỷ lệ (%)",
    ascending=False
)

# ----------------------------------------

# Trực quan hóa tỷ lệ giá trị thiếu
plt.figure(figsize=(10,6))

sns.barplot(
    data=missing.reset_index(),
    x="Tỷ lệ (%)",
    y="index",
    color="steelblue"
)

plt.title("Tỷ lệ giá trị thiếu theo thuộc tính")
plt.xlabel("Tỷ lệ (%)")
plt.ylabel("Thuộc tính")

plt.tight_layout()
plt.show()

# ----------------------------------------

duplicate_count = df.duplicated().sum()

print(f"Số dòng bị trùng lặp: {duplicate_count}")

# Hiển thị các dòng bị trùng (nếu có)
if duplicate_count > 0:
    display(df[df.duplicated()].head())
else:
    print("Không phát hiện dữ liệu trùng lặp.")

# ----------------------------------------

unique_summary = pd.DataFrame({
    "Thuộc tính": df.columns,
    "Số giá trị khác nhau": df.nunique().values
})

unique_summary = unique_summary.sort_values(
    by="Số giá trị khác nhau",
    ascending=False
).reset_index(drop=True)

unique_summary

# ----------------------------------------

#In ra giá trị và số lượng của các thuộc tính dạng categorical, để tìm ra phương án chuẩn hóa ở phần sau
categorical_cols = df.select_dtypes(include="object").columns

for col in categorical_cols:
    print("=" * 80)
    print(df[col].value_counts(dropna=False))
    print()

# ----------------------------------------

df.describe().T

# ----------------------------------------

# Lấy danh sách các thuộc tính số
numeric_cols = df.select_dtypes(include=np.number).columns

numeric_cols

# ----------------------------------------

# Vẽ Boxplot cho các thuộc tính số theo dạng lưới 2 cột

numeric_cols = df.select_dtypes(include=np.number).columns

n_cols = 2
n_rows = (len(numeric_cols) + n_cols - 1) // n_cols

fig, axes = plt.subplots(
    n_rows,
    n_cols,
    figsize=(14, 3 * n_rows)
)

# Chuyển axes thành mảng 1 chiều để dễ duyệt
axes = axes.flatten()

for i, col in enumerate(numeric_cols):
    sns.boxplot(
        x=df[col],
        ax=axes[i],
        color="skyblue"
    )

    axes[i].set_title(col, fontsize=11)
    axes[i].set_xlabel("")

# Xóa các subplot thừa (nếu số cột lẻ)
for i in range(len(numeric_cols), len(axes)):
    fig.delaxes(axes[i])

plt.suptitle("Biểu đồ Boxplot của các thuộc tính số", fontsize=14, fontweight="bold")
plt.tight_layout()

plt.show()

# ----------------------------------------

duplicate_count = df.duplicated().sum()

if duplicate_count > 0:
    df = df.drop_duplicates()
    print(f"Đã loại bỏ {duplicate_count} dòng dữ liệu trùng lặp.")
else:
    print("Không phát hiện dữ liệu trùng lặp.")

# ----------------------------------------

# Các cột phân loại
categorical_fill = {
    "House direction": "Không xác định",
    "Balcony direction": "Không xác định",
    "Legal status": "Không xác định",
    "Furniture state": "Không xác định"
}

# Thay thế giá trị thiếu của các cột phân loại
df.fillna(categorical_fill, inplace=True)

print("Đã xử lý giá trị thiếu cho các cột phân loại.")

# ----------------------------------------

# Các cột số cần xử lý giá trị thiếu
numeric_fill = [
    "Frontage",
    "Access Road",
    "Floors",
    "Bedrooms",
    "Bathrooms"
]

# Thay thế giá trị thiếu bằng trung vị của từng cột
for col in numeric_fill:
    df[col] = df[col].fillna(df[col].median())

print("Đã xử lý giá trị thiếu cho các cột số.")

# ----------------------------------------

# Chuẩn hóa tình trạng pháp lý
legal_mapping = {
    "Have certificate": "Đã có sổ",
    "Sale contract": "Hợp đồng mua bán"
}

df["Legal status"] = df["Legal status"].replace(legal_mapping)

print("Đã chuẩn hóa cột 'Legal status'.")

# ----------------------------------------

# Chuẩn hóa tình trạng nội thất
furniture_mapping = {
    "Full": "Đầy đủ",
    "Basic": "Cơ bản"
}

df["Furniture state"] = df["Furniture state"].replace(furniture_mapping)

print("Đã chuẩn hóa cột 'Furniture state'.")

# ----------------------------------------

# Tách địa chỉ thành danh sách
address_parts = df["Address"].str.split(",")

# Tỉnh/Thành phố
df["Province"] = address_parts.str[-1].str.strip().str.rstrip(".")

# Quận/Huyện
df["District"] = address_parts.str[-2].str.strip()

# Phường/Xã
df["Ward"] = address_parts.str[-3].str.strip()

# Phần còn lại của địa chỉ
df["Detail"] = address_parts.apply(
    lambda x: ", ".join([part.strip() for part in x[:-3]]) if len(x) > 3 else np.nan
)

print("Đã tách địa chỉ thành các cột 'Province', 'District', 'Ward' và 'Detail'.")

# ----------------------------------------

# Giá trên mỗi mét vuông
df["Price_per_m2"] = (df["Price"] / df["Area"]).round(2)

print("Đã tạo thuộc tính 'Price_per_m2'.")

# ----------------------------------------

# Các mốc phân vị của diện tích
area_quantiles = df["Area"].quantile([0, 0.2, 0.4, 0.6, 0.8, 1])

area_quantiles

# ----------------------------------------

area_bins = [0, 30, 50, 70, 90, np.inf]

area_labels = [
    "<30 m²",
    "30-50 m²",
    "50-70 m²",
    "70-90 m²",
    ">90 m²"
]

df["Area_Group"] = pd.cut(
    df["Area"],
    bins=area_bins,
    labels=area_labels,
    include_lowest=True
)

print("Đã tạo thuộc tính 'Area_Group'.")

# ----------------------------------------

# Các mốc phân vị của giá bán
price_quantiles = df["Price"].quantile([0, 0.2, 0.4, 0.6, 0.8, 1])

price_quantiles

# ----------------------------------------

price_bins = [0, 4, 6, 8, 10, np.inf]

price_labels = [
    "<4 tỷ",
    "4-6 tỷ",
    "6-8 tỷ",
    "8-10 tỷ",
    ">10 tỷ"
]

df["Price_Segment"] = pd.cut(
    df["Price"],
    bins=price_bins,
    labels=price_labels,
    include_lowest=True
)

print("Đã tạo thuộc tính 'Price_Segment'.")

# ----------------------------------------

# Kiểm tra thông tin dữ liệu
df.info()

# ----------------------------------------

df['Province'].unique()

# ----------------------------------------

# Chuẩn hóa các tên được viết tắt 
province_mapping = {
    "TPHCM": "Hồ Chí Minh",
    "TpHCM": "Hồ Chí Minh",
    "TP. HCM": "Hồ Chí Minh",
    "TP Hồ Chí Minh": "Hồ Chí Minh",
    "Hồ Chí Mính": "Hồ Chí Minh",
    "HN": "Hà Nội",
    "Hà Nội": "Hà Nội",
}

df["Province"] = df["Province"].replace(province_mapping)

# ----------------------------------------

# Giữ lại tên tỉnh nếu phía sau có thêm mô tả

df.loc[
    df["Province"].str.contains("Hồ Chí Minh", na=False),
    "Province"
] = "Hồ Chí Minh"

df.loc[
    df["Province"].str.contains("Bình Dương", na=False),
    "Province"
] = "Bình Dương"

df.loc[
    df["Province"].str.contains("Quảng Ninh", na=False),
    "Province"
] = "Quảng Ninh"

# ----------------------------------------

# Một số giá trị thực chất là quận/thành phố trực thuộc

province_mapping = {
    "Quận Bình Thạnh": "Hồ Chí Minh",
    "Quận 8": "Hồ Chí Minh",
    "Quận Nam Từ Liêm": "Hà Nội",
    "TP. Cam Ranh": "Khánh Hòa"
}

df["Province"] = df["Province"].replace(province_mapping)

# ----------------------------------------

# Các giá trị không phải tên tỉnh/thành

invalid_province = [
    "Đường số 11",
    "giá 6ty",
    "Phòng công chứng Nguyễn Thị Thành",
    "Bán nhà chính chủ Phó Đức Chính khu Bà Chiểu - trung tâm Bình Thạnh giá cực tốt",
    "Hồ Chí Minh giá 2tỷ380"
]

df.loc[
    df["Province"].isin(invalid_province),
    "Province"
] = "Không xác định"

# ----------------------------------------

df['Province'].unique()

# ----------------------------------------

# kiểm tra xem có giá trị thiếu trong cột Province không
df[df["Province"].isna()][["Address"]]

# ----------------------------------------

df[df["District"].isna()][["Address"]]

# ----------------------------------------

df[df["Ward"].isna()][["Address"]]

# ----------------------------------------

df["Province"] = df["Province"].replace(r"^\s*$", "Không xác định", regex=True)
df["District"] = df["District"].fillna("Không xác định")
df["Ward"] = df["Ward"].fillna("Không xác định")
df["Detail"] = df["Detail"].fillna("Không xác định")

# ----------------------------------------

# Chuẩn hóa tên Quận/Huyện trong cột District
import re

def clean_district(name):
    if not isinstance(name, str) or name.strip() in ("", "Không xác định", "nan"):
        return "Không xác định"
    s = name.strip()
    s = re.sub(r'\s+', ' ', s)
    # Loại bỏ các tiền tố hành chính nếu theo sau là tên tên riêng
    s_clean = re.sub(r'^(Huyện|Thị\s+[xX]ã|Quận|Thành\s+[pP]hố|TP\.?)\s+', '', s, flags=re.IGNORECASE).strip()
    
    # Nếu kết quả loại bỏ tiền tố chỉ chứa chữ số (ví dụ: '1', '2', '12'), giữ dạng 'Quận X'
    if s_clean.isdigit():
        return f"Quận {s_clean}"
    
    # Chuẩn hóa viết hoa chữ cái đầu mỗi từ
    words = s_clean.split(' ')
    s_clean = ' '.join([w.capitalize() if not w.isupper() else w for w in words])
    return s_clean

df["District"] = df["District"].apply(clean_district)
print(f"Đã chuẩn hóa cột District. Số giá trị unique sau chuẩn hóa: {df['District'].nunique()}")

# ----------------------------------------

# Kiểm tra thông tin dữ liệu sau khi xử lý
df.info()

# ----------------------------------------

df.isnull().sum()

# ----------------------------------------

df.duplicated().sum()

# ----------------------------------------

# Bảng tọa độ vĩ độ (Latitude) và kinh độ (Longitude) trung tâm các Tỉnh/Thành phố Việt Nam
PROVINCE_COORDINATES = {
    "Hồ Chí Minh": (10.7769, 106.7009),
    "Hà Nội": (21.0285, 105.8542),
    "Bình Dương": (11.1604, 106.6508),
    "Đà Nẵng": (16.0544, 108.2022),
    "Đồng Nai": (10.9454, 106.8248),
    "Hải Phòng": (20.8449, 106.6881),
    "Khánh Hòa": (12.2388, 109.1967),
    "Hưng Yên": (20.6464, 106.0511),
    "Long An": (10.5360, 106.4099),
    "Bà Rịa Vũng Tàu": (10.4114, 107.1362),
    "Bắc Ninh": (21.1861, 106.0763),
    "Bình Thuận": (11.0904, 108.0722),
    "Lâm Đồng": (11.9404, 108.4583),
    "Quảng Ninh": (21.0069, 107.2925),
    "Cần Thơ": (10.0452, 105.7469),
    "Thanh Hóa": (19.8067, 105.7852),
    "Kiên Giang": (10.0125, 105.0809),
    "Đắc Lắc": (12.6667, 108.0500),
    "Đắk Lắk": (12.6667, 108.0500),
    "Hà Nam": (20.5453, 105.9126),
    "Bình Định": (13.7820, 109.2194),
    "Quảng Nam": (15.5667, 108.4833),
    "Hòa Bình": (20.8133, 105.3383),
    "Phú Thọ": (21.3167, 105.2167),
    "Vĩnh Phúc": (21.3083, 105.6042),
    "Lào Cai": (22.4856, 103.9707),
    "Thừa Thiên Huế": (16.4637, 107.5909),
    "Nghệ An": (19.2342, 104.8920),
    "Bắc Giang": (21.2731, 106.1946),
    "Tiền Giang": (10.4493, 106.3422),
    "Thái Bình": (20.4464, 106.3364),
    "Thái Nguyên": (21.5928, 105.8442),
    "Tây Ninh": (11.3601, 106.1098),
    "Phú Yên": (13.0882, 109.3087),
    "Ninh Thuận": (11.5653, 108.9882),
    "Hà Tĩnh": (18.3428, 105.9056),
    "Hải Dương": (20.9374, 106.3146),
    "Quảng Trị": (16.7444, 107.1855),
    "Gia Lai": (13.9833, 108.0000),
    "Bến Tre": (10.2415, 106.3758),
    "An Giang": (10.3759, 105.4185),
    "Quảng Ngãi": (15.1205, 108.7923),
    "Bình Phước": (11.7500, 106.9167),
    "Sơn La": (21.3256, 103.9188),
    "Lạng Sơn": (21.8537, 106.7610),
    "Nam Định": (20.4200, 106.1683),
    "Yên Bái": (21.7167, 104.8833),
    "Vĩnh Long": (10.2537, 105.9722),
    "Trà Vinh": (9.9347, 106.3453),
    "Đồng Tháp": (10.4578, 105.6322),
    "Cà Mau": (9.1769, 105.1500),
    "Điện Biên": (21.3833, 103.0167),
    "Sóc Trăng": (9.6033, 105.9800),
    "Ninh Bình": (20.2506, 105.9745),
    "Bạc Liêu": (9.2941, 105.7244),
    "Tuyên Quang": (21.8242, 105.2158),
    "Hà Giang": (22.8233, 104.9839),
    "Hậu Giang": (9.7844, 105.4701),
    "Quảng Bình": (17.4690, 106.6227),
    "Kon Tum": (14.3500, 108.0000),
    "Cao Bằng": (22.6667, 105.9167),
    "Lai Châu": (22.4000, 103.4500),
    "Bắc Kạn": (22.1472, 105.8347),
    "Đắk Nông": (12.2500, 107.6833),
}

df["Latitude"] = df["Province"].map(lambda p: PROVINCE_COORDINATES.get(p, (np.nan, np.nan))[0])
df["Longitude"] = df["Province"].map(lambda p: PROVINCE_COORDINATES.get(p, (np.nan, np.nan))[1])


# ----------------------------------------

# Đường dẫn lưu bộ dữ liệu đã tiền xử lý
output_path = "../processed/house_price_clean.csv"

# Xuất dữ liệu
df.to_csv(
    output_path,
    index=False,
    encoding="utf-8-sig"
)

print(f"Đã xuất dữ liệu thành công tới: {output_path}")

# ----------------------------------------

df.info()

# ----------------------------------------
