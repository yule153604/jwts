# -*- coding: utf-8 -*-
import requests
import json
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re
import os
import sys

class ExamSystem:
    def __init__(self):
        self.base_url = "http://jw.cupk.edu.cn/jsxsd"
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Origin": "http://jw.cupk.edu.cn",
            "Referer": f"http://jw.cupk.edu.cn/jsxsd/"
        }
        # 推送接口配置
        self.push_token = os.getenv('PUSH_TOKEN', '')
        self.push_url = "https://www.pushplus.plus/send"

    def encode_inp(self, text):
        """实现JavaScript中的encodeInp函数"""
        key_str = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
        output = ""
        
        # Ensure text is bytes for ord to work as expected with multi-byte chars
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
            response = self.session.get(main_page_url, headers=self.headers, timeout=10)
            return response.status_code == 200 and "学生个人中心" in response.text
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
        encoded = f"{encoded_username}%%%{encoded_password}"
        
        data = {
            "encoded": encoded
        }
        
        try:
            # 首先访问基础URL获取会话cookies
            self.session.get(f"{self.base_url}/", headers=self.headers, timeout=10)
            
            response = self.session.post(login_url, data=data, headers=self.headers, timeout=10)
            
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

    def get_exam_page(self):
        """访问考试查询页面"""
        if not self.check_login_status():
            print("用户未登录或会话已过期。")
            return None

        exam_url = "http://jw.cupk.edu.cn/jsxsd/xsks/xsksap_query"
        
        try:
            response = self.session.get(exam_url, headers=self.headers, timeout=15)
            response.raise_for_status()

            if "统一身份认证" in response.text or "用户登录" in response.text:
                print("会话可能已过期或重定向到登录页。请尝试重新运行脚本。")
                return None

            print("成功访问考试查询页面！")
            return response.text
            
        except requests.exceptions.Timeout:
            print("获取考试页面超时。")
            return None
        except requests.exceptions.RequestException as e:
            print(f"获取考试页面时发生网络错误: {str(e)}")
            return None
        except Exception as e:
            print(f"获取考试页面时发生错误: {str(e)}")
            return None

    def get_exam_list(self, xnxqid="2024-2025-2"):
        """获取考试安排列表"""
        if not self.check_login_status():
            print("用户未登录或会话已过期。")
            return None

        exam_list_url = "http://jw.cupk.edu.cn/jsxsd/xsks/xsksap_list"
        
        # 构建请求数据
        data = {
            "xnxqid": xnxqid  # 学年学期ID
        }
        
        try:
            response = self.session.post(exam_list_url, data=data, headers=self.headers, timeout=15)
            response.raise_for_status()

            if "统一身份认证" in response.text or "用户登录" in response.text:
                print("会话可能已过期或重定向到登录页。请尝试重新运行脚本。")
                return None

            print(f"成功获取 {xnxqid} 学期的考试安排！")
            return response.text
            
        except requests.exceptions.Timeout:
            print("获取考试安排列表超时。")
            return None
        except requests.exceptions.RequestException as e:
            print(f"获取考试安排列表时发生网络错误: {str(e)}")
            return None
        except Exception as e:
            print(f"获取考试安排列表时发生错误: {str(e)}")
            return None

    def parse_exam_list(self, html_content):
        """解析考试安排列表HTML"""
        if not html_content:
            print("HTML内容为空，无法解析。")
            return []

        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 查找考试数据表格
            exam_table = soup.find('table', {'id': 'dataList'})
            if not exam_table:
                print("未找到考试数据表格。")
                return []

            exams = []
            rows = exam_table.find_all('tr')[1:]  # 跳过表头
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 9:
                    # 提取考试信息
                    exam_info = {
                        'index': cells[0].text.strip(),
                        'exam_id': cells[1].text.strip(),
                        'course_code': cells[2].text.strip(),
                        'course_name': cells[3].text.strip(),
                        'exam_time': cells[4].text.strip(),
                        'exam_room': cells[5].text.strip(),
                        'seat_number': cells[6].text.strip(),
                        'exam_method': cells[7].text.strip(),
                        'remarks': cells[8].text.strip()
                    }
                    exams.append(exam_info)
            
            return exams
            
        except Exception as e:
            print(f"解析考试安排列表时发生错误: {str(e)}")
            return []

    def get_term_options(self, html_content):
        """从页面中解析可用的学期选项"""
        if not html_content:
            return []
            
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            select = soup.find('select', {'id': 'xnxqid'})
            if not select:
                return []
                
            options = []
            for option in select.find_all('option'):
                value = option.get('value')
                text = option.text.strip()
                selected = 'selected' in option.attrs
                options.append({
                    'value': value,
                    'text': text,
                    'selected': selected
                })
            return options
        except Exception as e:
            print(f"获取学期选项时发生错误: {str(e)}")
            return []

    def format_exam_time(self, time_str):
        """格式化考试时间，提取日期、开始时间和结束时间"""
        try:
            parts = time_str.split(' ')
            if len(parts) == 2:
                date = parts[0]
                times = parts[1].split('~')
                if len(times) == 2:
                    start_time = times[0]
                    end_time = times[1]
                    return {
                        'date': date,
                        'start_time': start_time,
                        'end_time': end_time,
                        'full': time_str
                    }
            return {
                'date': '',
                'start_time': '',
                'end_time': '',
                'full': time_str
            }
        except Exception:
            return {
                'date': '',
                'start_time': '',
                'end_time': '',
                'full': time_str
            }

    def sort_exams_by_date(self, exams):
        """按日期排序考试"""
        if not exams:
            return []
            
        def get_date(exam):
            exam_time = self.format_exam_time(exam['exam_time'])
            if exam_time['date']:
                try:
                    return datetime.strptime(exam_time['date'], '%Y-%m-%d')
                except ValueError:
                    return datetime.max
            return datetime.max
            
        return sorted(exams, key=get_date)

    def get_upcoming_exams(self, exams, days=7):
        """获取即将到来的考试（默认7天内）"""
        if not exams:
            return []
            
        today = datetime.now()
        upcoming = []
        
        for exam in exams:
            exam_time = self.format_exam_time(exam['exam_time'])
            if exam_time['date']:
                try:
                    exam_date = datetime.strptime(exam_time['date'], '%Y-%m-%d')
                    days_until = (exam_date - today).days
                    if 0 <= days_until <= days:
                        exam['days_until'] = days_until
                        upcoming.append(exam)
                except ValueError:
                    continue
                    
        return upcoming

    def count_days_until_exam(self, exam_date_str):
        """计算距离考试还有多少天"""
        try:
            exam_date = datetime.strptime(exam_date_str, '%Y-%m-%d')
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            delta = exam_date - today
            return delta.days
        except ValueError:
            return None

    def push_exams(self, exams, term_name):
        """推送考试安排到微信"""
        if not exams:
            print("没有考试安排可推送。")
            return False
            
        try:
            # 获取当前日期
            today = datetime.now()
            date_str = today.strftime("%Y-%m-%d")
            
            # 按日期排序考试
            sorted_exams = self.sort_exams_by_date(exams)
            
            # 获取即将到来的考试
            upcoming_exams = self.get_upcoming_exams(sorted_exams)
            
            # 构建推送内容
            content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px;">
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                    <h2 style="color: #2c3e50; margin: 0; text-align: center;">{term_name}考试安排</h2>
                    <p style="color: #7f8c8d; text-align: center; margin-top: 5px;">共 {len(exams)} 门考试</p>
                </div>
            """
            
            # 如果有即将到来的考试，优先显示
            if upcoming_exams:
                content += f"""
                <div style="background-color: #fff3cd; padding: 10px; border-radius: 5px; margin-bottom: 20px; border-left: 4px solid #ffc107;">
                    <h3 style="color: #856404; margin-top: 0;">⚠️ 近期考试提醒</h3>
                    <ul style="padding-left: 20px;">
                """
                for exam in upcoming_exams:
                    exam_time = self.format_exam_time(exam['exam_time'])
                    days_text = "今天" if exam['days_until'] == 0 else f"{exam['days_until']}天后"
                    content += f"""
                    <li style="margin-bottom: 8px;">
                        <span style="font-weight: bold;">{exam['course_name']}</span> - 
                        <span style="color: #e74c3c;">{exam_time['date']} ({days_text})</span> 
                        <span>{exam_time['start_time']}-{exam_time['end_time']}</span>, 
                        <span>地点: {exam['exam_room']}</span>
                    </li>
                    """
                content += """
                    </ul>
                </div>
                """
            
            # 所有考试的详细表格
            content += """
                <table style="width: 100%; border-collapse: collapse; margin-top: 20px; box-shadow: 0 2px 3px rgba(0,0,0,0.1);">
                    <thead>
                        <tr style="background-color: #4a90e2; color: white;">
                            <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">课程</th>
                            <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">日期</th>
                            <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">时间</th>
                            <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">地点</th>
                            <th style="padding: 12px; text-align: center; border: 1px solid #ddd;">剩余天数</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            for i, exam in enumerate(sorted_exams):
                exam_time = self.format_exam_time(exam['exam_time'])
                days_until = self.count_days_until_exam(exam_time['date'])
                
                # 设置背景色：过期为灰色，即将考试为黄色，其他为白色或浅灰色
                bg_color = "#ffffff"
                days_text = "未知"
                days_color = "#666666"
                
                if days_until is not None:
                    if days_until < 0:
                        bg_color = "#f1f1f1"  # 灰色背景表示已过期
                        days_text = "已结束"
                        days_color = "#999999"
                    elif days_until == 0:
                        bg_color = "#fff3cd"  # 黄色背景表示今天
                        days_text = "今天"
                        days_color = "#e74c3c"
                    elif days_until <= 7:
                        bg_color = "#fcf8e3"  # 浅黄色背景表示一周内
                        days_text = f"{days_until}天"
                        days_color = "#e67e22"
                    else:
                        days_text = f"{days_until}天"
                        bg_color = "#ffffff" if i % 2 == 0 else "#f8f9fa"  # 交替行背景色
                
                content += f"""
                    <tr style="background-color: {bg_color};">
                        <td style="padding: 12px; border: 1px solid #ddd;">
                            <div style="font-weight: bold;">{exam['course_name']}</div>
                            <div style="font-size: 12px; color: #666;">{exam['course_code']}</div>
                        </td>
                        <td style="padding: 12px; border: 1px solid #ddd;">{exam_time['date']}</td>
                        <td style="padding: 12px; border: 1px solid #ddd;">{exam_time['start_time']}~{exam_time['end_time']}</td>
                        <td style="padding: 12px; border: 1px solid #ddd;">{exam['exam_room']}</td>
                        <td style="padding: 12px; border: 1px solid #ddd; text-align: center; color: {days_color}; font-weight: bold;">{days_text}</td>
                    </tr>
                """
            
            content += """
                    </tbody>
                </table>
                <div style="margin-top: 20px; text-align: center; color: #666; font-size: 12px;">
                    <p>考试安排可能随时变动，请以教务系统公告为准</p>
                    <p>此消息由教务系统自动推送</p>
                </div>
            </div>
            """
            
            # 构建推送参数
            title = f"📝 {term_name}考试安排 ({date_str})"
            params = {
                "token": self.push_token,
                "title": title,
                "content": content,
                "template": "html"
            }
            
            # 发送推送请求
            response = requests.post(self.push_url, json=params)
            result = response.json()
            
            if result.get("code") == 200:
                print("考试安排推送成功！")
                return True
            else:
                print(f"考试安排推送失败：{result.get('msg', '未知错误')}")
                return False
                
        except Exception as e:
            print(f"推送考试安排时发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

def main():
    try:
        # 从环境变量获取账号密码
        username = os.getenv('JW_USERNAME', '')
        password = os.getenv('JW_PASSWORD', '')

        if not username or not password:
            print("提示：未在环境变量中找到 JW_USERNAME 或 JW_PASSWORD。")
            print("请设置环境变量或在代码中提供测试账号。")
            # 为了测试，您可以在这里直接设置用户名和密码
            # username = "your_username"
            # password = "your_password"
            if not username or not password:
                print("错误：请提供用户名和密码。")
                sys.exit(1)

        exam_system = ExamSystem()
        
        print(f"尝试使用学号 {username} 登录教务系统...")
        if exam_system.login(username, password):
            print("\n登录成功，开始访问考试查询页面...")
            
            # 获取考试查询页面
            html_content = exam_system.get_exam_page()
            
            if html_content:
                print("\n成功获取考试查询页面，正在解析可用学期...")
                
                # 获取学期选项
                term_options = exam_system.get_term_options(html_content)
                
                if term_options:
                    # 找到默认选中的学期
                    selected_term = next((option for option in term_options if option['selected']), None)
                    
                    if selected_term:
                        term_id = selected_term['value']
                        term_name = selected_term['text']
                        print(f"\n默认选中学期: {term_name} (ID: {term_id})")
                        
                        # 获取考试安排
                        exam_list_html = exam_system.get_exam_list(term_id)
                        
                        if exam_list_html:
                            print(f"\n成功获取考试安排，正在解析...")
                            
                            # 解析考试安排
                            exams = exam_system.parse_exam_list(exam_list_html)
                            
                            if exams:
                                print(f"\n找到 {len(exams)} 门考试安排:")
                                
                                # 按日期排序考试
                                sorted_exams = exam_system.sort_exams_by_date(exams)
                                
                                # 打印考试信息
                                for i, exam in enumerate(sorted_exams, 1):
                                    exam_time = exam_system.format_exam_time(exam['exam_time'])
                                    days_until = exam_system.count_days_until_exam(exam_time['date'])
                                    days_text = "未知" if days_until is None else (
                                        "今天" if days_until == 0 else (
                                            "已结束" if days_until < 0 else f"还有 {days_until} 天"
                                        )
                                    )
                                    
                                    print(f"\n{i}. {exam['course_name']} ({exam['course_code']})")
                                    print(f"   考试时间: {exam_time['full']} ({days_text})")
                                    print(f"   考场地点: {exam['exam_room']}")
                                    if exam['seat_number']:
                                        print(f"   座位号: {exam['seat_number']}")
                                    if exam['exam_method']:
                                        print(f"   考试方式: {exam['exam_method']}")
                                    if exam['remarks']:
                                        print(f"   备注: {exam['remarks']}")
                                  # 推送到微信
                                print("\n正在检查是否有近期考试...")
                                upcoming_exams = exam_system.get_upcoming_exams(sorted_exams)
                                
                                if upcoming_exams:
                                    print(f"找到 {len(upcoming_exams)} 门近期考试，准备推送微信提醒...")
                                    if exam_system.push_exams(exams, term_name):
                                        print("考试安排已成功推送！")
                                    else:
                                        print("考试安排推送失败。")
                                else:
                                    print("没有近期考试（一周内），无需推送微信提醒。")
                            else:
                                print("未找到考试安排。")
                        else:
                            print("获取考试安排失败。")
                    else:
                        print("未找到默认选中的学期。")
                else:
                    print("未找到学期选项。")
            else:
                print("获取考试查询页面失败。")
        else:
            print("登录失败，无法获取考试安排。")
    except Exception as e:
        print(f"程序执行出错: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()