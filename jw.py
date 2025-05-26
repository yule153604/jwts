import requests
import base64
import json
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re
import os
import sys

class JWSystem:
    def __init__(self):
        self.base_url = "http://jw.cupk.edu.cn/jsxsd"
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Origin": "http://jw.cupk.edu.cn",
            "Referer": "http://jw.cupk.edu.cn/jsxsd/"
        }
        # 设置第一周周一日期
        self.first_week_monday = datetime(2025, 3, 3)
        # 推送接口配置
        self.push_token = os.getenv('PUSH_TOKEN', '')
        self.push_url = "https://www.pushplus.plus/send"

    def get_current_week(self):
        """计算当前是第几周"""
        today = datetime.now()
        # 计算与第一周周一的日期差
        days_diff = (today - self.first_week_monday).days
        # 计算周数（向上取整）
        current_week = (days_diff // 7) + 1
        return max(1, current_week)  # 确保周数至少为1

    def parse_course_info(self, cell):
        """解析课程信息"""
        try:
            course_div = cell.find('div', {'class': 'kbcontent1'})
            if not course_div:
                return None
            
            course_text = course_div.text.strip()
            if not course_text or course_text == '\xa0':
                return None
                
            # 分割课程信息
            info_parts = course_text.split('\n')
            if not info_parts:
                return None
                
            # 解析课程名称和基本信息
            course_info = {
                'name': '',
                'weeks': '',
                'classroom': '',
                'course_code': ''
            }
            
            # 处理第一行（课程名称、周次、教室、课程号等混合信息）
            if info_parts[0]:
                full_text = info_parts[0].strip()
                
                # 1. 提取课程号
                course_code_match = re.search(r'\d{6}[A-Z]\d{3}-\d{2}', full_text)
                if course_code_match:
                    course_info['course_code'] = course_code_match.group()
                    full_text = full_text.replace(course_info['course_code'], '', 1).strip()
                
                # 2. 提取周次信息
                weeks_match = re.search(r'\d+-\d+\(周\)', full_text)
                if weeks_match:
                    course_info['weeks'] = weeks_match.group()
                    full_text = full_text.replace(course_info['weeks'], '', 1).strip()
                
                # 3. 处理剩余的 full_text 来分离课程名称和教室
                potential_classroom_keywords = ["机房", "实验室", "教室"]
                
                building_marker_match = re.search(r'[A-Z]\d+楼', full_text)
                
                if building_marker_match:
                    # 情况1：找到了楼号标记 (例如 "C4楼")
                    name_candidate = full_text[:building_marker_match.start()].strip()
                    classroom_candidate = full_text[building_marker_match.start():].strip()

                    # 检查 name_candidate 是否以关键字结尾，如果是，则移到 classroom_candidate
                    for keyword in potential_classroom_keywords:
                        if name_candidate.endswith(keyword):
                            name_candidate = name_candidate[:-len(keyword)].strip()
                            classroom_candidate = keyword + " " + classroom_candidate # 将关键字前置到教室信息
                            break 
                    
                    course_info['name'] = name_candidate
                    course_info['classroom'] = classroom_candidate
                else:
                    # 情况2：没有找到楼号标记
                    # 尝试基于关键字从 full_text 末尾提取教室信息
                    name_part = full_text
                    classroom_part = ""
                    for keyword in potential_classroom_keywords:
                        if name_part.endswith(keyword):
                            # 如果 full_text 以关键字结尾 (例如 "课程名称 机房" 或 "课程机房" 或 "机房")
                            # 将关键字视为教室，其余部分为名称
                            classroom_part = keyword
                            name_part = name_part[:-len(keyword)].strip()
                            break
                    course_info['name'] = name_part
                    course_info['classroom'] = classroom_part
                
                # 如果名称和教室都未解析出来，但 full_text 仍有内容 (在移除代码和周次后)
                # 意味着之前的逻辑未能分离名称和教室，此时将剩余 full_text 赋给名称
                if not course_info['name'] and not course_info['classroom'] and full_text:
                    course_info['name'] = full_text

            return course_info
            
        except Exception as e:
            print(f"解析课程信息时出错: {str(e)}")
            return None

    def get_schedule(self):
        """获取课表信息"""
        try:
            # 获取当前周数
            current_week = self.get_current_week()
            print(f"正在获取第{current_week}周的课表...")
            
            # 构建请求参数
            schedule_url = f"{self.base_url}/xskb/xskb_list.do"
            params = {
                "Ves632DSdyV": "NEW_XSD_PYGL",
                "zc1": str(current_week),
                "zc2": str(current_week),
                "xnxq01id": "2024-2025-2"  # 当前学期
            }
            
            # 发送请求获取课表
            response = self.session.get(schedule_url, params=params, headers=self.headers)
            
            if response.status_code == 200:
                # 使用BeautifulSoup解析HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 获取课表信息
                schedule_data = []
                table = soup.find('table', {'id': 'kbtable'})
                
                if not table:
                    print("未找到课表数据")
                    return None
                
                # 获取所有行
                rows = table.find_all('tr')
                if len(rows) <= 1:  # 只有表头或没有数据
                    print("课表数据为空")
                    return None
                
                # 处理每一行（跳过表头）
                for row in rows[1:]:
                    try:
                        cells = row.find_all(['th', 'td'])
                        if not cells or len(cells) < 8:  # 确保有足够的单元格
                            continue
                            
                        time_slot = cells[0].text.strip()
                        
                        # 处理周一到周日的课程
                        for i in range(1, 8):
                            if i < len(cells):  # 确保索引有效
                                course_info = self.parse_course_info(cells[i])
                                if course_info:
                                    schedule_data.append({
                                        'time': time_slot,
                                        'day': i,
                                        'course': course_info
                                    })
                    except Exception as e:
                        print(f"处理行数据时出错: {str(e)}")
                        continue
                
                if not schedule_data:
                    print("本周没有课程安排")
                    return None
                    
                return {
                    'current_week': current_week,
                    'schedule': schedule_data
                }
            else:
                print(f"获取课表失败，状态码：{response.status_code}")
                return None
                
        except Exception as e:
            print(f"获取课表时发生错误: {str(e)}")
            return None

    def encode_inp(self, text):
        """实现JavaScript中的encodeInp函数"""
        key_str = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
        output = ""
        i = 0
        
        while i < len(text):
            chr1 = ord(text[i])
            i += 1
            chr2 = ord(text[i]) if i < len(text) else 0
            i += 1
            chr3 = ord(text[i]) if i < len(text) else 0
            i += 1
            
            enc1 = chr1 >> 2
            enc2 = ((chr1 & 3) << 4) | (chr2 >> 4)
            enc3 = ((chr2 & 15) << 2) | (chr3 >> 6)
            enc4 = chr3 & 63
            
            if chr2 == 0:
                enc3 = enc4 = 64
            elif chr3 == 0:
                enc4 = 64
                
            output += key_str[enc1] + key_str[enc2] + key_str[enc3] + key_str[enc4]
            
        return output

    def check_login_status(self):
        """检查登录状态"""
        try:
            main_page_url = "http://jw.cupk.edu.cn/jsxsd/framework/xsMain.jsp"
            response = self.session.get(main_page_url, headers=self.headers)
            return response.status_code == 200
        except Exception as e:
            print(f"检查登录状态时发生错误: {str(e)}")
            return False

    def login(self, username, password):
        """登录教务系统"""
        login_url = f"{self.base_url}/xk/LoginToXk"
        
        # 编码用户名和密码
        encoded_username = self.encode_inp(username)
        encoded_password = self.encode_inp(password)
        encoded = f"{encoded_username}%%%{encoded_password}"
        
        data = {
            "encoded": encoded
        }
        
        try:
            # 首先访问登录页面获取cookie
            self.session.get(f"{self.base_url}/", headers=self.headers)
            
            # 发送登录请求
            response = self.session.post(login_url, data=data, headers=self.headers)
            
            # 打印响应信息用于调试
            print(f"登录请求状态码: {response.status_code}")
            print(f"登录请求响应头: {json.dumps(dict(response.headers), indent=2, ensure_ascii=False)}")
            
            # 检查登录状态
            if self.check_login_status():
                print("登录成功！")
                return True
            else:
                print("登录失败，请检查用户名和密码！")
                if "验证码" in response.text:
                    print("需要验证码，请稍后添加验证码处理功能")
                return False
        except Exception as e:
            print(f"登录过程中发生错误: {str(e)}")
            return False

    def convert_time(self, time_code):
        """转换时间代码为具体时间"""
        time_map = {
            "0102": "9:30-11:05",
            "0304": "11:20-12:55",
            "0405": "12:10-13:45",
            "0607": "16:00-17:35",
            "0809": "17:50-19:25"
        }
        return time_map.get(time_code, time_code)

    def push_schedule(self, schedule):
        """推送课表到微信"""
        try:
            # 获取当前日期和星期
            now = datetime.now()
            # 判断是否在20点之前
            is_before_8pm = now.hour < 20
            
            # 确定目标日期
            target_date = now
            if not is_before_8pm:
                target_date = now + timedelta(days=1)
            
            weekday = target_date.weekday() + 1  # 转换为1-7的星期格式
            date_str = target_date.strftime("%Y-%m-%d")
            
            # 构建推送内容
            content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px;">
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                    <h2 style="color: #2c3e50; margin: 0; text-align: center;">{date_str} 课表</h2>
                </div>
                <table style="width: 100%; border-collapse: collapse; margin-top: 20px; box-shadow: 0 2px 3px rgba(0,0,0,0.1);">
                    <thead>
                        <tr style="background-color: #4a90e2; color: white;">
                            <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">时间</th>
                            <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">星期</th>
                            <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">课程</th>
                            <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">周次</th>
                            <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">教室</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            # 筛选目标日期的课程
            filtered_schedule = [course for course in schedule['schedule'] if course['day'] == weekday]
            
            # 打印课表到控制台
            print(f"\n--- {date_str} 课表 ({'今天' if target_date.date() == now.date() else '明天'}) --- ")
            if not filtered_schedule:
                print(f"{date_str} 没有课程安排")
            else:
                for course in filtered_schedule:
                    course_info = course['course']
                    print(f"时间：{self.convert_time(course['time'])}, 星期{course['day']}")
                    print(f"课程名称：{course_info['name']}")
                    if course_info['weeks']:
                        print(f"上课周次：{course_info['weeks']}")
                    if course_info['classroom']:
                        print(f"上课教室：{course_info['classroom']}")
                    if course_info['course_code']:
                        print(f"课程编号：{course_info['course_code']}")
                    print("-" * 30)
            print("--- 课表结束 ---\n")
            
            if not filtered_schedule:
                content += f"""
                    <tr>
                        <td colspan="5" style="padding: 15px; text-align: center; border: 1px solid #ddd; background-color: #f8f9fa;">
                            <span style="color: #666; font-style: italic;">{date_str} 没有课程安排</span>
                        </td>
                    </tr>
                """
            
            for i, course in enumerate(filtered_schedule):
                course_info = course['course']
                # 交替行背景色
                bg_color = "#ffffff" if i % 2 == 0 else "#f8f9fa"
                content += f"""
                    <tr style="background-color: {bg_color};">
                        <td style="padding: 12px; border: 1px solid #ddd;">{self.convert_time(course['time'])}</td>
                        <td style="padding: 12px; border: 1px solid #ddd;">星期{course['day']}</td>
                        <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">{course_info['name']}</td>
                        <td style="padding: 12px; border: 1px solid #ddd;">{course_info['weeks']}</td>
                        <td style="padding: 12px; border: 1px solid #ddd;">{course_info['classroom']}</td>
                    </tr>
                """
            
            content += """
                    </tbody>
                </table>
                <div style="margin-top: 20px; text-align: center; color: #666; font-size: 12px;">
                    <p>此消息由教务系统自动推送</p>
                </div>
            </div>
            """
            
            # 构建推送参数
            title = f"📚 {date_str} 课表"
            params = {
                "token": self.push_token,
                "title": title,
                "content": content,
                "template": "html"
            }
            
            # 发送推送请求
            response = requests.post(self.push_url, data=params)
            print(f"PushPlus API Status Code: {response.status_code}") 
            print(f"PushPlus API Response Text: {response.text}") 
            
            # 检查响应文本是否为空
            if not response.text:
                print("课表推送失败：PushPlus API 返回了空响应。")
                return

            try:
                result = response.json()
                if result.get("code") == 200:
                    print("课表推送成功！")
                else:
                    print(f"课表推送失败：{result.get('msg')}")
            except requests.exceptions.JSONDecodeError as e:
                print(f"课表推送失败：无法解析 PushPlus API 的响应为 JSON。错误信息: {e}")
                print(f"原始响应状态码: {response.status_code}")
                print(f"原始响应文本: {response.text}")
                
        except Exception as e:
            print(f"推送课表时发生错误: {str(e)}")

def main():
    try:
        # 从环境变量获取账号密码
        username = os.getenv('JW_USERNAME','')
        password = os.getenv('JW_PASSWORD','')
        
        jw = JWSystem()
        if jw.login(username, password):
            # 获取课表信息
            schedule = jw.get_schedule()
            if schedule:
                # 推送课表到微信
                jw.push_schedule(schedule)
    except Exception as e:
        print(f"程序执行出错: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
