import os
import re
import sys
import time
import csv
import argparse
import json
from bs4 import BeautifulSoup
import random
from DrissionPage import WebPage, ChromiumOptions

# Đảm bảo stdout sử dụng UTF-8 để tránh lỗi font chữ trên Terminal
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

CSV_COLUMNS = [
    'Address', 'Area', 'Frontage', 'Access Road', 
    'House direction', 'Balcony direction', 
    'Bedrooms', 'Bathrooms', 'Legal status', 'Furniture state', 
    'Price', 'Day'
]

DEFAULT_CATEGORIES = [
    ("Bán Căn hộ chung cư", "https://batdongsan.com.vn/ban-can-ho-chung-cu"),
    ("Bán Chung cư mini, căn hộ dịch vụ", "https://batdongsan.com.vn/ban-can-ho-chung-cu-mini"),
    ("Bán Nhà riêng", "https://batdongsan.com.vn/ban-nha-rieng"),
    ("Bán Nhà biệt thự, liền kề", "https://batdongsan.com.vn/ban-nha-biet-thu-lien-ke"),
    ("Bán Nhà mặt phố", "https://batdongsan.com.vn/ban-nha-mat-pho"),
    ("Bán Shophouse, nhà phố thương mại", "https://batdongsan.com.vn/ban-shophouse-nha-pho-thuong-mai"),
    ("Bán Đất nền dự án", "https://batdongsan.com.vn/ban-dat-nen-du-an"),
    ("Bán Đất", "https://batdongsan.com.vn/ban-dat"),
    ("Bán Trang trại, khu nghỉ dưỡng", "https://batdongsan.com.vn/ban-trang-trai-khu-nghi-duong"),
    ("Bán Condotel", "https://batdongsan.com.vn/ban-condotel"),
    ("Bán Kho, nhà xưởng", "https://batdongsan.com.vn/ban-kho-nha-xuong"),
    ("Bán Loại BĐS khác", "https://batdongsan.com.vn/ban-loai-bat-dong-san-khac")
]

def parse_price(price_str):
    """Xử lý chuỗi giá thành giá trị số thực (Đơn vị: Tỷ)."""
    if not price_str:
        return None
    price_str = price_str.lower().strip()
    if 'thỏa thuận' in price_str or 'thoa thuan' in price_str:
        return None
    
    tỷ_val = 0.0
    triệu_val = 0.0
    
    tỷ_match = re.search(r'([\d.,]+)\s*tỷ', price_str)
    triệu_match = re.search(r'([\d.,]+)\s*triệu', price_str)
    
    found = False
    if tỷ_match:
        tỷ_val = float(tỷ_match.group(1).replace(',', '.'))
        found = True
    if triệu_match:
        triệu_val = float(triệu_match.group(1).replace(',', '.')) / 1000.0
        found = True
        
    if found:
        return round(tỷ_val + triệu_val, 2)
        
    try:
        cleaned = re.sub(r'[^\d.,]', '', price_str).replace(',', '.')
        if cleaned:
            val = float(cleaned)
            if 'triệu' in price_str:
                return round(val / 1000.0, 3)
            return val
    except ValueError:
        pass
    return None

def parse_detail_html(html_content, detail_url):
    """Phân tích HTML trang chi tiết bất động sản."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Địa chỉ
    address = None
    addr_el = soup.select_one('.js__pr-address, .re__pr-short-info-item .re__list-standard-title')
    if addr_el:
        address = addr_el.get_text(' ', strip=True)
    if not address:
        breads = soup.select('.re__breadcrumb a')
        if len(breads) > 1:
            address = ', '.join([b.get_text(strip=True) for b in breads[1:]])

    if address:
        address = re.sub(r'\s*,\s*', ', ', address)
        address = re.sub(r'^,\s*', '', address)
        address = re.sub(r'\s+', ' ', address).strip()

    area = frontage = access_road = house_dir = balcony_dir = floors = bedrooms = bathrooms = legal = furniture = price_val = None
    day = month = year = None
    
    # Đọc thông tin ngày từ JSON-LD schema
    for s in soup.find_all('script', type='application/ld+json'):
        try:
            if not s.string:
                continue
            data = json.loads(s.string)
            if isinstance(data, dict) and data.get('@type') == 'RealEstateListing' and 'datePublished' in data:
                date_m = re.search(r'(\d{4})-(\d{2})-(\d{2})', data['datePublished'])
                if date_m:
                    year = int(date_m.group(1))
                    month = int(date_m.group(2))
                    day = int(date_m.group(3))
        except Exception:
            pass

    # Đọc các thông số kỹ thuật
    spec_items = soup.select('.re__pr-specs-content-item, .re__pr-config-item')
    for item in spec_items:
        title_el = item.select_one('.re__pr-specs-content-item-title, .title')
        val_el = item.select_one('.re__pr-specs-content-item-value, .value')
        
        full_text = item.get_text(' ', strip=True)
        lbl = title_el.get_text(strip=True).lower() if title_el else full_text.lower()
        val = val_el.get_text(strip=True) if val_el else full_text
        
        if 'diện tích' in lbl and not area:
            area = val
        elif 'mặt tiền' in lbl and not frontage:
            frontage = val
        elif 'đường vào' in lbl and not access_road:
            access_road = val
        elif 'hướng nhà' in lbl and not house_dir:
            house_dir = val
        elif 'hướng ban công' in lbl and not balcony_dir:
            balcony_dir = val
        elif ('số phòng ngủ' in lbl or 'phòng ngủ' in lbl) and not bedrooms:
            bedrooms = val
        elif ('số phòng tắm' in lbl or 'vệ sinh' in lbl or 'toilet' in lbl) and not bathrooms:
            bathrooms = val
        elif 'pháp lý' in lbl and not legal:
            legal = val
        elif 'nội thất' in lbl and not furniture:
            furniture = val
        elif ('mức giá' in lbl or 'khoảng giá' in lbl or 'giá' in lbl) and not price_val:
            price_val = val
        elif 'ngày đăng' in lbl and not day:
            date_m = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', val)
            if date_m:
                day = int(date_m.group(1))
                month = int(date_m.group(2))
                year = int(date_m.group(3))

    # Đọc ngày đăng từ khu vực thông tin ngắn
    for el in soup.select('.re__pr-short-info-item'):
        text = el.get_text(' ', strip=True)
        if 'Ngày đăng' in text and not day:
            date_m = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', text)
            if date_m:
                day = int(date_m.group(1))
                month = int(date_m.group(2))
                year = int(date_m.group(3))

    # Phân loại danh mục từ URL để hỗ trợ phân tích diện tích
    url_lower = str(detail_url).lower()
    is_large_area_category = any(k in url_lower for k in ['ban-dat', 'ban-kho-nha-xuong', 'ban-trang-trai', 'ban-loai-bat-dong-san-khac'])

    # Làm sạch các trường dữ liệu số
    def safe_float_convert(val_str, is_area=False):
        if not val_str:
            return None
        
        # Rút trích phần chuỗi chứa số và các dấu phân cách
        m = re.search(r'([\d.,\s]+)', str(val_str))
        if not m:
            return None
            
        num_str = m.group(1).strip()
        # Loại bỏ khoảng trắng giữa các chữ số (ví dụ: "12 500" -> "12500")
        num_str = re.sub(r'\s+', '', num_str)
        
        # 1. Trường hợp có cả dấu chấm và dấu phẩy (ví dụ: "1.250,5" hoặc "1,250.5")
        if '.' in num_str and ',' in num_str:
            dot_idx = num_str.rfind('.')
            comma_idx = num_str.rfind(',')
            if dot_idx > comma_idx:
                # Dấu chấm là thập phân, dấu phẩy là phần ngàn
                num_str = num_str.replace(',', '')
            else:
                # Dấu phẩy là thập phân, dấu chấm là phần ngàn
                num_str = num_str.replace('.', '').replace(',', '.')
                
        # 2. Chỉ có dấu phẩy (ví dụ: "12,5" hoặc "12,500")
        elif ',' in num_str:
            if num_str.count(',') > 1:
                # Nhiều dấu phẩy -> Chắc chắn là phân cách phần ngàn
                num_str = num_str.replace(',', '')
            else:
                # 1 dấu phẩy
                left, right = num_str.split(',')
                if len(right) == 3:
                    # Trường hợp mơ hồ: có thể là thập phân (tiếng Việt) hoặc phần ngàn (tiếng Anh)
                    try:
                        dec_val = float(left + '.' + right)
                    except ValueError:
                        dec_val = 0.0
                    
                    if is_area:
                        if dec_val < 30.0 or is_large_area_category:
                            # Coi là phần ngàn
                            num_str = left + right
                        else:
                            # Coi là thập phân
                            num_str = left + '.' + right
                    else:
                        # Kích thước tuyến tính (mặt tiền / đường vào) -> luôn là thập phân
                        num_str = left + '.' + right
                else:
                    # Không phải 3 chữ số phía sau -> thập phân
                    num_str = left + '.' + right

        # 3. Chỉ có dấu chấm (ví dụ: "12.5" hoặc "12.500")
        elif '.' in num_str:
            if num_str.count('.') > 1:
                # Nhiều dấu chấm -> phần ngàn
                num_str = num_str.replace('.', '')
            else:
                # 1 dấu chấm
                left, right = num_str.split('.')
                if len(right) == 3:
                    # Trường hợp mơ hồ: có thể là phần ngàn (tiếng Việt) hoặc thập phân (tiếng Anh)
                    try:
                        dec_val = float(left + '.' + right)
                    except ValueError:
                        dec_val = 0.0
                    
                    if is_area:
                        if dec_val < 30.0 or is_large_area_category:
                            # Coi là phần ngàn
                            num_str = left + right
                        else:
                            # Coi là thập phân
                            num_str = left + '.' + right
                    else:
                        # Kích thước tuyến tính -> luôn là thập phân
                        num_str = left + '.' + right
                else:
                    # Không phải 3 chữ số phía sau -> thập phân
                    pass
                    
        try:
            return float(num_str)
        except ValueError:
            return None # Trả về None nếu vẫn lỗi, đảm bảo script không bao giờ bị crash

    area = safe_float_convert(area, is_area=True)
    frontage = safe_float_convert(frontage, is_area=False)
    access_road = safe_float_convert(access_road, is_area=False)
    
    if bedrooms:
        m = re.search(r'(\d+)', str(bedrooms))
        bedrooms = int(m.group(1)) if m else None
    if bathrooms:
        m = re.search(r'(\d+)', str(bathrooms))
        bathrooms = int(m.group(1)) if m else None
    price = parse_price(price_val)
    
    if legal:
        l_low = str(legal).lower()
        if 'sổ đỏ' in l_low or 'sổ hồng' in l_low or 'đã có sổ' in l_low:
            legal = 'Have certificate'
        elif 'hợp đồng mua bán' in l_low or 'hđmb' in l_low:
            legal = 'Sale contract'
        else:
            legal = None
            
    if furniture:
        f_low = str(furniture).lower()
        if 'đầy đủ' in f_low or 'full' in f_low:
            furniture = 'Full'
        elif 'cơ bản' in f_low or 'co ban' in f_low:
            furniture = 'Basic'
        else:
            furniture = None

    return {
        'Address': address,
        'Area': area,
        'Frontage': frontage,
        'Access Road': access_road,
        'House direction': house_dir if house_dir else None,
        'Balcony direction': balcony_dir if balcony_dir else None,
        'Bedrooms': bedrooms,
        'Bathrooms': bathrooms,
        'Legal status': legal,
        'Furniture state': furniture,
        'Price': price,
        'Day': day,
        '_month_internal': month,
        '_year_internal': year
    }

def extract_detail_links_from_html(html_content, base_url="https://batdongsan.com.vn"):
    """Rút trích tất cả liên kết bài đăng chi tiết từ HTML trang danh sách."""
    soup = BeautifulSoup(html_content, 'html.parser')
    links = []
    seen = set()
    
    for a in soup.find_all('a', href=True):
        href = a['href']
        if '/ban-' in href and ('-pr' in href or href.endswith('.htm')):
            full_url = href if href.startswith('http') else base_url + href
            if full_url not in seen:
                seen.add(full_url)
                links.append(full_url)
                
    return links

def main():
    parser = argparse.ArgumentParser(description="Batdongsan.com.vn Fast Hybrid Crawler")
    parser.add_argument("--cat-indices", type=int, nargs='+', help="Các chỉ số danh mục cần cào (1-12). Ví dụ: --cat-indices 8")
    parser.add_argument("--start-page", type=int, default=1200, help="Trang bắt đầu (mặc định: 1200)")
    parser.add_argument("--end-page", type=int, default=1, help="Trang kết thúc (mặc định: 1)")
    parser.add_argument("--target-month", type=int, default=6, help="Tháng mục tiêu (mặc định: 6)")
    parser.add_argument("--target-year", type=int, default=2026, help="Năm mục tiêu (mặc định: 2026)")
    parser.add_argument("--request-delay", type=float, default=0.5, help="Thời gian nghỉ giữa các HTTP request để đảm bảo rate limit (giây, mặc định: 0.5)")
    parser.add_argument("--output", type=str, default="house_price_crawl.csv", help="Tên file CSV đầu ra")
    
    args, _ = parser.parse_known_args()
    
    if args.cat_indices:
        selected_cats = [DEFAULT_CATEGORIES[i - 1] for i in args.cat_indices if 1 <= i <= len(DEFAULT_CATEGORIES)]
    else:
        selected_cats = DEFAULT_CATEGORIES

    if args.start_page > args.end_page:
        page_range = list(range(args.start_page, args.end_page - 1, -1))
    else:
        page_range = list(range(args.start_page, args.end_page + 1))

    print("=" * 65)
    print("   Batdongsan.com.vn Fast Hybrid Crawler (WebPage Mode)")
    print(f"   Selected Categories: {len(selected_cats)}/{len(DEFAULT_CATEGORIES)}")
    print(f"   Target Month/Year: Tháng {args.target_month}/{args.target_year}")
    print(f"   Page Direction: {page_range[0]} -> {page_range[-1]} | Output: {args.output}")
    print(f"   Request Delay: {args.request_delay}s")
    print("=" * 65)

    output_csv = args.output
    crawled_urls = set()
    file_exists = os.path.exists(output_csv)
    
    csv_file = open(output_csv, mode='a' if file_exists else 'w', newline='', encoding='utf-8')
    writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS)
    if not file_exists:
        writer.writeheader()
        csv_file.flush()

    total_saved = 0
    start_time = time.time()
    
    # Cấu hình tối ưu cho trình duyệt Chromium
    co = ChromiumOptions()
    co.set_argument('--blink-settings=imagesEnabled=false') 
    co.set_pref('profile.managed_default_content_settings.images', 2)
    co.set_pref('profile.managed_default_content_settings.stylesheets', 2)
    co.set_pref('profile.managed_default_content_settings.fonts', 2)

    # Khởi tạo WebPage (Tích hợp trình duyệt lẫn HTTP Session)
    page = WebPage(chromium_options=co)
    try:
        page.set.load_mode.eager()
        page.set.timeouts(page_load=5, script=5)
    except Exception:
        pass

    try:
        for cat_idx, (cat_name, cat_url) in enumerate(selected_cats, 1):
            print(f"\n[{cat_idx}/{len(selected_cats)}] Category Branch: '{cat_name}' ({cat_url})")
            has_started_saving_target = False
            
            for page_num in page_range:
                page_index_url = cat_url if page_num == 1 else f"{cat_url}/p{page_num}"
                
                try:
                    # Mở trang danh sách bằng trình duyệt thật để lấy cookie & đồng bộ session
                    page.get(page_index_url)
                    detail_links = extract_detail_links_from_html(page.html)
                except Exception as e:
                    print(f"    Error fetching index page {page_index_url}: {e}")
                    continue

                if not detail_links:
                    print(f"    Page {page_num}: No detail links found. Skipping...")
                    continue

                new_links = [l for l in detail_links if l not in crawled_urls]
                for l in new_links:
                    crawled_urls.add(l)
                        
                if not new_links:
                    continue

                target_saved_on_this_page = 0
                older_than_target_hit = False
                newer_hit_count = 0

                # Lặp qua từng bài đăng chi tiết
                for link in new_links:
                    try:
                        # QUAY LẠI DÙNG TRÌNH DUYỆT THẬT ĐỂ QUA MẶT CLOUDFLARE
                        page.get(link)
                        
                        # Kiểm soát Rate Limit
                        if args.request_delay > 0:
                            sleep_time = random.uniform(0.1, args.request_delay)
                            time.sleep(sleep_time)
                            # time.sleep(args.request_delay)
                            
                        # Dùng page.html thay vì res.html
                        row_data = parse_detail_html(page.html, link)
                        
                        if row_data:
                            item_m = row_data.get('_month_internal')
                            item_y = row_data.get('_year_internal')
                            
                            # DEBUG: Báo lỗi nếu không lấy được ngày (do cấu trúc đổi hoặc bị chặn)
                            if not item_m or not item_y:
                                print(f"    [Cảnh báo] Không đọc được ngày đăng (Có thể trang bị lỗi hoặc bắt xác minh): {link}")
                                continue
                            
                            csv_row = {k: v for k, v in row_data.items() if k in CSV_COLUMNS}
                            
                            # Trường hợp 1: Bài viết thuộc tháng mục tiêu -> Lưu vào CSV
                            if item_m == args.target_month and item_y == args.target_year:
                                writer.writerow(csv_row)
                                csv_file.flush()
                                total_saved += 1
                                target_saved_on_this_page += 1
                                has_started_saving_target = True
                                elapsed = time.time() - start_time
                                speed = total_saved / elapsed if elapsed > 0 else 0
                                print(f"    -> Saved entry ({csv_row.get('Day')}/{args.target_month:02d}/{args.target_year}) | Page {page_num} | Total: {total_saved} ({speed:.2f} items/s)")
                            
                            # Trường hợp 2: Gặp bài viết cũ hơn tháng mục tiêu -> Chuyển sang trang tiếp theo
                            elif item_m and (item_y < args.target_year or (item_y == args.target_year and item_m < args.target_month)):
                                print(f"    [Month {item_m}/{item_y} < Target {args.target_month}/{args.target_year}] Encountered older item. Switching to next page!")
                                older_than_target_hit = True
                                break
                            
                            # Trường hợp 3: Gặp bài viết mới hơn tháng mục tiêu -> Bỏ qua bài viết
                            elif item_m and (item_y > args.target_year or (item_y == args.target_year and item_m > args.target_month)):
                                newer_hit_count += 1
                                continue
                    except Exception as e:
                        print(f"    [Lỗi xử lý link] {link} - Error: {e}")

                # Kết thúc nhánh danh mục nếu đã hoàn tất dữ liệu tháng mục tiêu
                if has_started_saving_target and target_saved_on_this_page == 0 and newer_hit_count > 0:
                    print(f"    [Terminated] Reached end of target month listings on page {page_num}. Ending branch for '{cat_name}'.")
                    break

    finally:
        page.quit()
        csv_file.close()

    print("=" * 65)
    print(f"Crawl Finished! Total Month {args.target_month}/{args.target_year} entries saved: {total_saved}")
    print(f"Total time elapsed: {time.time() - start_time:.1f} seconds")
    print("=" * 65)

if __name__ == '__main__':
    main()