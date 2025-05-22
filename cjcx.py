import requests
import json
from datetime import datetime
from bs4 import BeautifulSoup
import re
import os
import sys

class GradeSystem:
    def __init__(self):
        self.base_url = "http://jw.cupk.edu.cn/jsxsd"
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Origin": "http://jw.cupk.edu.cn",
            "Referer": f"{self.base_url}/"
        }
        # 推送接口配置
        self.push_token = os.getenv('PUSH_TOKEN') # Replace with your token or use env var
        self.push_url = "https://www.pushplus.plus/send"
        # 文件用于存储上一次查询的成绩
        self.previous_grades_file = "previous_grades_data.json"

    def encode_inp(self, text):
        """实现JavaScript中的encodeInp函数"""
        key_str = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
        output = ""
        i = 0
        
        # Ensure text is bytes for ord to work as expected with multi-byte chars
        # The original JS function processes char codes. Python's ord() on a string
        # gives Unicode code points. For direct JS equivalence with charCodeAt on what
        # might be a UTF-8 stream interpreted as individual bytes by the JS, 
        # we should encode to UTF-8 first and iterate over bytes.
        text_bytes = text.encode('utf-8') 

        idx = 0
        while idx < len(text_bytes):
            chr1 = text_bytes[idx]
            idx += 1
            # Pad with 0 if source string is not a multiple of 3 bytes
            chr2 = text_bytes[idx] if idx < len(text_bytes) else 0
            idx += 1
            chr3 = text_bytes[idx] if idx < len(text_bytes) else 0
            idx += 1
            
            enc1 = chr1 >> 2
            enc2 = ((chr1 & 3) << 4) | (chr2 >> 4)
            enc3 = ((chr2 & 15) << 2) | (chr3 >> 6)
            enc4 = chr3 & 63
            
            # Padding characters for Base64
            if chr2 == 0: 
                enc3 = enc4 = 64
            elif chr3 == 0:
                enc4 = 64
                
            output += key_str[enc1] + key_str[enc2] + key_str[enc3] + key_str[enc4]
            
        return output

    def check_login_status(self):
        """检查登录状态"""
        try:
            main_page_url = f"{self.base_url}/framework/xsMain.jsp"
            # Add a timeout to prevent indefinite hanging
            response = self.session.get(main_page_url, headers=self.headers, timeout=10)
            # A more robust check might involve looking for specific content on the main page
            # that only appears when logged in.
            return response.status_code == 200 and "学生个人中心" in response.text # Example check
        except requests.exceptions.RequestException as e:
            print(f"检查登录状态时发生网络错误: {str(e)}")
            return False
        except Exception as e:
            print(f"检查登录状态时发生错误: {str(e)}")
            return False

    def login(self, username, password):
        """登录教务系统"""
        login_url = f"{self.base_url}/xk/LoginToXk"
        
        encoded_username = self.encode_inp(username)
        encoded_password = self.encode_inp(password)
        
        # The JS code from the user for encodeInp implies a Base64-like encoding.
        # The login form data for 'encoded' is typically username%%%password, both parts encoded.
        encoded = f"{encoded_username}%%%{encoded_password}"
        
        data = {
            "encoded": encoded
            # Other fields like userAccount, userPassword, randCode might be needed by some systems
            # but are not present in the jw.py example for this specific login.
        }
        
        try:
            # It's good practice to visit the base URL or login page first to get session cookies.
            self.session.get(f"{self.base_url}/", headers=self.headers, timeout=10)
            
            response = self.session.post(login_url, data=data, headers=self.headers, timeout=10)
            
            # print(f"登录请求状态码: {response.status_code}") # For debugging
            # print(f"登录请求响应内容 (前500字符): {response.text[:500]}") # For debugging

            if self.check_login_status():
                print("登录成功！")
                return True
            else:
                print("登录失败。")
                if "验证码" in response.text:
                    print("登录失败，可能需要验证码。请检查教务系统登录页面。")
                elif "用户名或密码错误" in response.text or "密码不正确" in response.text or "用户名不存在" in response.text:
                     print("登录失败，用户名或密码错误。")
                else:
                    # print(f"登录失败，未知错误。响应: {response.text[:200]}") # More debug info
                    print("登录失败，未知错误。请检查网络或教务系统状态。")
                return False
        except requests.exceptions.Timeout:
            print(f"登录过程中发生超时错误。")
            return False
        except requests.exceptions.RequestException as e:
            print(f"登录过程中发生网络错误: {str(e)}")
            return False
        except Exception as e:
            print(f"登录过程中发生未知错误: {str(e)}")
            return False

    def get_grades(self):
        """获取常规成绩信息"""
        if not self.check_login_status():
            print("用户未登录或会话已过期。")
            return None

        grades_url = f"{self.base_url}/kscj/cjcx_list?Ves632DSdyV=NEW_XSD_XJCJ"
        try:
            response = self.session.get(grades_url, headers=self.headers, timeout=15)
            response.raise_for_status() 

            if "统一身份认证" in response.text or "用户登录" in response.text and "kscj/cjcx_list" not in response.url:
                print("会话可能已过期或重定向到登录页。请尝试重新运行脚本。")
                return None

            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table', {'id': 'dataList'})
            
            if not tables or len(tables) < 1: # Only need the first table
                print("未找到常规成绩数据表。HTML内容可能已更改或非预期。")
                return None

            regular_grades_data = {'regular_grades': []} # Initialize for regular grades only

            # --- Parse first table (regular grades) ---
            regular_grades_table = tables[0]
            rows = regular_grades_table.find_all('tr')
            if len(rows) > 1: 
                for row_idx, row in enumerate(rows[1:]): 
                    cols = row.find_all('td')
                    if len(cols) == 14: 
                        grade = {
                            'index': cols[0].text.strip(),
                            'semester': cols[1].text.strip(),
                            'course_code': cols[2].text.strip(),
                            'course_name': cols[3].text.strip(),
                            'score': cols[4].text.strip(),
                            'credit': cols[5].text.strip(),
                            'total_hours': cols[6].text.strip(),
                            'gpa': cols[7].text.strip(),
                            'assessment_method': cols[8].text.strip(),
                            'course_attribute': cols[9].text.strip(),
                            'course_nature': cols[10].text.strip(),
                            'exam_nature': cols[11].text.strip(),
                            'retake_semester': cols[12].text.strip(),
                            'score_flag': cols[13].text.strip(),
                        }
                        regular_grades_data['regular_grades'].append(grade)
            
            if not regular_grades_data['regular_grades']: # Check only regular grades
                print("常规成绩数据为空或未能解析。")
                return None
                    
            return regular_grades_data # Return only regular grades data
        except requests.exceptions.Timeout:
            print("获取成绩超时。")
            return None
        except requests.exceptions.RequestException as e:
            print(f"获取成绩时发生网络错误: {str(e)}")
            return None
        except Exception as e:
            print(f"获取成绩时发生解析错误或未知错误: {str(e)}")
            # import traceback
            # traceback.print_exc() # For detailed error info during development
            return None

    def load_previous_grades(self):
        """从文件加载先前保存的成绩"""
        try:
            if os.path.exists(self.previous_grades_file):
                with open(self.previous_grades_file, 'r', encoding='utf-8') as f:
                    print(f"从 {self.previous_grades_file} 加载先前成绩...")
                    return json.load(f)
        except Exception as e:
            print(f"加载先前成绩时出错: {e}")
        return {'regular_grades': []} # 返回空结构以避免后续错误

    def save_grades(self, grades_data):
        """将当前成绩保存到文件"""
        try:
            with open(self.previous_grades_file, 'w', encoding='utf-8') as f:
                json.dump(grades_data, f, ensure_ascii=False, indent=4)
            print(f"当前成绩已保存到 {self.previous_grades_file}")
        except Exception as e:
            print(f"保存当前成绩时出错: {e}")

    def compare_grades(self, current_grades_list, previous_grades_list):
        """比较两组成绩列表是否有差异"""
        if not previous_grades_list and current_grades_list: # 首次获取或之前为空
             return True
        if len(current_grades_list) != len(previous_grades_list):
            return True

        # 为比较创建规范表示形式
        # 我们将每个成绩字典转换为其键值对的排序元组，
        # 以确保字典内的顺序不影响比较。
        # 然后我们对这些元组的列表进行排序。
        def canonical_grade(grade_dict):
            # 选择定义成绩条目及其状态的关键字段
            # 如果“index”可能会在实际成绩未更改的情况下更改，则排除它
            return tuple(sorted((k, grade_dict.get(k)) for k in [
                'semester', 'course_code', 'course_name', 'score', 
                'credit', 'gpa', 'assessment_method', 'course_attribute', 
                'course_nature', 'exam_nature', 'retake_semester', 'score_flag'
            ]))

        current_canonical = sorted([canonical_grade(g) for g in current_grades_list])
        previous_canonical = sorted([canonical_grade(g) for g in previous_grades_list])

        return current_canonical != previous_canonical

    def push_grades_notification(self, grades_data, username=""):
        """推送常规成绩到微信"""
        if not grades_data or not grades_data.get('regular_grades'): # Check only regular grades
            print("没有常规成绩数据可推送。")
            return

        try:
            today_date = datetime.now().strftime("%Y-%m-%d")
            user_info = f"学号 {username} 的" if username else ""
            title = f"📚 {user_info}成绩通知 - {today_date}"
            
            # Reduced font size and padding for compactness
            table_font_size = "12px" # Was 13px
            cell_padding = "5px"    # Was 10px
            h2_font_size = "20px"   # Was 22px
            h3_font_size = "16px"   # Was 18px
            footer_font_size = "11px" # Was 12px

            content = f"""
            <div style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; max-width: 1000px; margin: 20px auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px; background-color: #f9f9f9;">
                <div style="background-color: #007bff; color: white; padding: 15px; border-radius: 8px 8px 0 0; margin: -20px -20px 20px -20px;">
                    <h2 style="margin: 0; text-align: center; font-size: {h2_font_size};">{user_info}个人成绩单</h2>
                </div>
            """

            if grades_data.get('regular_grades'):
                content += f"""
                <h3 style="color: #333; margin-top: 20px; margin-bottom: 8px; border-bottom: 2px solid #007bff; padding-bottom: 4px; font-size: {h3_font_size};">详细成绩</h3>
                <table style="width: 100%; border-collapse: collapse; margin-top: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); font-size: {table_font_size};">
                    <thead>
                        <tr style="background-color: #f0f0f0; color: #333; font-weight: bold;">
                            <th style="padding: {cell_padding}; text-align: left; border: 1px solid #ddd;">序号</th>
                            <th style="padding: {cell_padding}; text-align: left; border: 1px solid #ddd;">开课学期</th>
                            <th style="padding: {cell_padding}; text-align: left; border: 1px solid #ddd;">课程名称</th>
                            <th style="padding: {cell_padding}; text-align: center; border: 1px solid #ddd;">成绩</th>
                            <th style="padding: {cell_padding}; text-align: center; border: 1px solid #ddd;">学分</th>
                            <th style="padding: {cell_padding}; text-align: center; border: 1px solid #ddd;">绩点</th>
                            <th style="padding: {cell_padding}; text-align: left; border: 1px solid #ddd;">课程属性</th>
                            <th style="padding: {cell_padding}; text-align: left; border: 1px solid #ddd;">考试性质</th>
                        </tr>
                    </thead>
                    <tbody>
                """
                for i, grade in enumerate(grades_data['regular_grades']):
                    bg_color = "#ffffff" if i % 2 == 0 else "#f7f7f7"
                    score_val = grade['score']
                    score_style = ""
                    # Apply style based on score value
                    if score_val.isdigit():
                        try:
                            numeric_score = int(score_val)
                            if numeric_score < 60:
                                score_style = "font-weight: bold; color: #d9534f;" # Red for fail
                            elif numeric_score >= 90:
                                score_style = "font-weight: bold; color: #5cb85c;" # Green for high score
                        except ValueError:
                            pass # Should not happen if isdigit() is true, but good for safety
                    
                    content += f"""
                        <tr style="background-color: {bg_color};">
                            <td style="padding: {cell_padding}; border: 1px solid #ddd;">{grade['index']}</td>
                            <td style="padding: {cell_padding}; border: 1px solid #ddd;">{grade['semester']}</td>
                            <td style="padding: {cell_padding}; border: 1px solid #ddd; font-weight: bold;">{grade['course_name']} ({grade['course_code']})</td>
                            <td style="padding: {cell_padding}; border: 1px solid #ddd; text-align: center; {score_style}">{score_val}</td>
                            <td style="padding: {cell_padding}; border: 1px solid #ddd; text-align: center;">{grade['credit']}</td>
                            <td style="padding: {cell_padding}; border: 1px solid #ddd; text-align: center;">{grade['gpa'] if grade['gpa'] else '-'}</td>
                            <td style="padding: {cell_padding}; border: 1px solid #ddd;">{grade['course_attribute']}</td>
                            <td style="padding: {cell_padding}; border: 1px solid #ddd;">{grade['exam_nature']}</td>
                        </tr>
                    """
                content += "</tbody></table>"

            content += f"""
                <div style="margin-top: 25px; text-align: center; color: #777; font-size: {footer_font_size};">
                    <p>数据获取时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                    <p>此消息由教务助手自动推送</p>
                </div>
            </div>
            """
            
            params = {
                "token": self.push_token,
                "title": title,
                "content": content,
                "template": "html"
            }
            
            response = requests.post(self.push_url, data=params, timeout=10) # Use POST for pushplus
            result = response.json()
            
            if result.get("code") == 200:
                print("成绩推送成功！")
            else:
                print(f"成绩推送失败：{result.get('msg')} (Code: {result.get('code')})")
                # print(f"Pushplus Response: {result}") # For debugging push issues
                
        except requests.exceptions.RequestException as e:
            print(f"推送成绩时发生网络错误: {str(e)}")
        except Exception as e:
            print(f"推送成绩时发生错误: {str(e)}")
            # import traceback
            # traceback.print_exc()

def main():
    username = os.getenv('JW_USERNAME')
    password = os.getenv('JW_PASSWORD')

    if not username or not password:
        print("提示：未在环境变量中找到 JW_USERNAME 或 JW_PASSWORD。")
        # Fallback for testing - REMOVE FOR PRODUCTION/SHARING
        # print("使用内置的测试账号 (仅供测试，请及时替换为环境变量)。")
        # username = "" # Replace with actual username for testing only
        # password = ""   # Replace with actual password for testing only
        # if not username or not password: # If even fallback is not set
        #    print("错误：请设置 JW_USERNAME 和 JW_PASSWORD 环境变量或在代码中提供测试账号。")
        #    sys.exit(1)
        # Using default from jw.py for now as per user context
        print("使用jw.py中的默认账户测试")
        username = "" 
        password = "" 

    grade_system = GradeSystem()
    
    # 加载上次的成绩
    previous_grades_data = grade_system.load_previous_grades()
    # 从加载的数据中提取实际的成绩列表，如果键不存在则默认为空列表
    previous_filtered_grades_list = previous_grades_data.get('regular_grades', [])

    print(f"尝试使用学号 {username} 登录教务系统...")
    if grade_system.login(username, password):
        print("\\n登录成功，开始获取成绩信息...")
        current_grades_full_data = grade_system.get_grades()
        
        if current_grades_full_data and current_grades_full_data.get('regular_grades'):
            print("\\n成功获取常规成绩信息。")

            # Determine current academic year string
            now = datetime.now()
            current_year = now.year
            # Academic year typically starts around August/September.
            # If current month is before August, academic year is (Year-1)-Year.
            # Otherwise, it's Year-(Year+1).
            if now.month < 8: 
                academic_year_str = f"{current_year - 1}-{current_year}"
            else:
                academic_year_str = f"{current_year}-{current_year + 1}"
            
            print(f"\\n当前学年 (用于筛选): {academic_year_str}")

            # Filter grades for the current academic year
            current_academic_year_grades = [
                g for g in current_grades_full_data['regular_grades']
                if g['semester'].startswith(academic_year_str)
            ]

            if current_academic_year_grades:
                print(f"\\n--- {academic_year_str}学年 常规成绩 ---")
                for g in current_academic_year_grades:
                    print(f"  学期: {g['semester']}, 课程: {g['course_name']} ({g['course_code']}), 成绩: {g['score']}, 学分: {g['credit']}, 绩点: {g['gpa']}")
                
                grades_to_push_dict = {'regular_grades': current_academic_year_grades}
                
                # 比较成绩是否有变动
                if grade_system.compare_grades(current_academic_year_grades, previous_filtered_grades_list):
                    print(f"\\n检测到成绩变动或首次查询，准备推送 {academic_year_str} 学年常规成绩通知...")
                    grade_system.push_grades_notification(grades_to_push_dict, username)
                    grade_system.save_grades(grades_to_push_dict) # 保存新的成绩记录
                else:
                    print(f"\\n{academic_year_str} 学年常规成绩未发生变动，无需推送。")
            else:
                print(f"\\n在 {academic_year_str} 学年未找到常规成绩记录。")
                # 如果当前学年没有成绩，但之前有成绩记录，也视为变动，并清空已存记录
                if grade_system.compare_grades([], previous_filtered_grades_list):
                     print(f"\\n检测到成绩变动（当前学年无成绩，但先前有记录），将清空已存成绩记录。")
                     grade_system.save_grades({'regular_grades': []})
                elif not previous_filtered_grades_list: # 如果之前就没有成绩，现在也没有，则无需操作
                    print(f"\\n先前也无 {academic_year_str} 学年成绩记录，无需操作。")


        else:
            print("\\n未能获取常规成绩信息或成绩为空。不进行比较或推送。")
    else:
        print("\\n登录失败，无法继续获取成绩。请检查账号密码及网络连接。")

if __name__ == "__main__":
    # Ensure the script can find modules if it's structured with other local files
    # sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    main()
