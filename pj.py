import requests
import json
from datetime import datetime
from bs4 import BeautifulSoup
import re
import os
import sys

class EvaluationSystem:
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

    def get_evaluation_page(self):
        """访问评教页面并获取响应"""
        if not self.check_login_status():
            print("用户未登录或会话已过期。")
            return None

        evaluation_url = "http://jw.cupk.edu.cn/jsxsd/xspj/xspj_find.do"
        
        try:
            response = self.session.get(evaluation_url, headers=self.headers, timeout=15)
            response.raise_for_status()

            if "统一身份认证" in response.text or "用户登录" in response.text:
                print("会话可能已过期或重定向到登录页。请尝试重新运行脚本。")
                return None

            print("成功访问评教页面！")
            return response.text
            
        except requests.exceptions.Timeout:
            print("获取评教页面超时。")
            return None
        except requests.exceptions.RequestException as e:
            print(f"获取评教页面时发生网络错误: {str(e)}")
            return None
        except Exception as e:
            print(f"获取评教页面时发生错误: {str(e)}")
            return None

    def parse_evaluation_links(self, html_content):
        """解析评教页面，提取评教链接"""
        if not html_content:
            print("HTML内容为空，无法解析。")
            return []

        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 查找包含评教链接的表格
            evaluation_links = []
            
            # 查找所有带有"进入评价"的链接
            links = soup.find_all('a', string='进入评价')
            
            for link in links:
                href = link.get('href')
                if href:
                    # 构建完整的URL
                    if href.startswith('/'):
                        full_url = f"http://jw.cupk.edu.cn{href}"
                    else:
                        full_url = href
                    
                    # 查找该链接所在行的其他信息
                    row = link.find_parent('tr')
                    if row:
                        cells = row.find_all('td')
                        if len(cells) >= 6:
                            evaluation_info = {
                                'url': full_url,
                                'index': cells[0].text.strip(),
                                'semester': cells[1].text.strip(),
                                'category': cells[2].text.strip(),
                                'batch': cells[3].text.strip(),
                                'start_time': cells[4].text.strip(),
                                'end_time': cells[5].text.strip()
                            }
                            evaluation_links.append(evaluation_info)
            
            return evaluation_links
            
        except Exception as e:
            print(f"解析评教链接时发生错误: {str(e)}")
            return []

    def display_evaluation_info(self, evaluation_links):
        """显示评教信息"""
        if not evaluation_links:
            print("未找到评教链接。")
            return

        print("\n=== 评教信息 ===")
        for i, info in enumerate(evaluation_links, 1):
            print(f"\n{i}. 评教项目:")
            print(f"   学年学期: {info['semester']}")
            print(f"   评价分类: {info['category']}")
            print(f"   评价批次: {info['batch']}")
            print(f"   开始时间: {info['start_time']}")
            print(f"   结束时间: {info['end_time']}")
            print(f"   评教链接: {info['url']}")

    def get_course_list(self, evaluation_url):
        """访问具体的评教课程列表页面"""
        if not self.check_login_status():
            print("用户未登录或会话已过期。")
            return None

        try:
            response = self.session.get(evaluation_url, headers=self.headers, timeout=15)
            response.raise_for_status()

            if "统一身份认证" in response.text or "用户登录" in response.text:
                print("会话可能已过期或重定向到登录页。请尝试重新运行脚本。")
                return None

            print("成功访问评教课程列表页面！")
            return response.text
            
        except requests.exceptions.Timeout:
            print("获取评教课程列表页面超时。")
            return None
        except requests.exceptions.RequestException as e:
            print(f"获取评教课程列表页面时发生网络错误: {str(e)}")
            return None
        except Exception as e:
            print(f"获取评教课程列表页面时发生错误: {str(e)}")
            return None

    def parse_course_list(self, html_content):
        """解析课程列表，查找未提交的评教"""
        if not html_content:
            print("HTML内容为空，无法解析。")
            return []

        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 查找课程数据表格
            course_table = soup.find('table', {'id': 'dataList'})
            if not course_table:
                print("未找到课程数据表格。")
                return []

            courses = []
            rows = course_table.find_all('tr')[1:]  # 跳过表头
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 9:
                    # 提取课程信息
                    course_info = {
                        'index': cells[0].text.strip(),
                        'course_code': cells[1].text.strip(),
                        'course_name': cells[2].text.strip(),
                        'teacher': cells[3].text.strip(),
                        'evaluation_type': cells[4].text.strip(),
                        'total_score': cells[5].text.strip(),
                        'is_evaluated': cells[6].text.strip(),
                        'is_submitted': cells[7].text.strip(),
                        'operation_cell': cells[8]
                    }
                    
                    # 查找操作链接
                    operation_links = cells[8].find_all('a')
                    evaluation_link = None
                    
                    for link in operation_links:
                        href = link.get('href')
                        if href and 'xspj_edit.do' in href:
                            # 提取评教链接
                            if href.startswith('javascript:openWindow('):                                # 提取括号内的URL部分
                                start = href.find("'") + 1
                                end = href.find("'", start)
                                if start > 0 and end > start:
                                    evaluation_link = href[start:end]
                                    if evaluation_link.startswith('/'):
                                        evaluation_link = f"http://jw.cupk.edu.cn{evaluation_link}"
                            
                    course_info['evaluation_link'] = evaluation_link
                    courses.append(course_info)
            
            return courses
            
        except Exception as e:
            print(f"解析课程列表时发生错误: {str(e)}")
            return []
    
    def find_unevaluated_courses(self, courses):
        """查找未提交评教的课程"""
        unevaluated = []
        for course in courses:
            if course['is_submitted'] == '否':
                unevaluated.append(course)
        
        return unevaluated
    
    def perform_evaluation(self, course_info):
        """对指定课程进行评教"""
        if not course_info.get('evaluation_link'):
            print(f"课程 {course_info['course_name']} 没有找到评教链接。")
            return False

        evaluation_url = course_info['evaluation_link']
        
        try:
            print(f"正在访问课程 {course_info['course_name']} 的评教页面...")
            response = self.session.get(evaluation_url, headers=self.headers, timeout=15)
            response.raise_for_status()

            if "统一身份认证" in response.text or "用户登录" in response.text:
                print("会话可能已过期或重定向到登录页。")
                return False

            print(f"成功访问课程 {course_info['course_name']} 的评教页面！")
            
            # 解析评教表单
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找评教表单
            form = soup.find('form', {'id': 'Form1'})
            if not form:
                print(f"未找到评教表单。")
                return False

            print(f"找到评教表单，准备自动选择A选项并提交...")
            
            # 准备表单数据
            form_data = {}
            
            # 1. 收集所有隐藏字段
            hidden_inputs = form.find_all('input', {'type': 'hidden'})
            for hidden_input in hidden_inputs:
                name = hidden_input.get('name')
                value = hidden_input.get('value', '')
                if name:
                    form_data[name] = value
            
            # 2. 处理主要评价指标 (pj0601id_ 字段) - 选择A选项
            pj_inputs = form.find_all('input', {'name': re.compile(r'pj0601id_\d+')})
            pj_groups = {}
            
            # 按组分类
            for pj_input in pj_inputs:
                name = pj_input.get('name')
                value = pj_input.get('value')
                if name and value:
                    if name not in pj_groups:
                        pj_groups[name] = []
                    pj_groups[name].append({
                        'value': value,
                        'input': pj_input
                    })
            
            # 为每个评价指标选择第一个选项（A选项）
            for group_name, options in pj_groups.items():
                if options:
                    # 选择第一个选项（A选项）
                    form_data[group_name] = options[0]['value']
                    print(f"  - 评价指标 {group_name}: 选择A选项")
            
            # 3. 处理问卷调查 (tmid_ 字段) - 选择A选项  
            tmid_inputs = form.find_all('input', {'name': re.compile(r'tmid_[A-F0-9]+')})
            tmid_groups = {}
            
            # 按组分类
            for tmid_input in tmid_inputs:
                name = tmid_input.get('name')
                value = tmid_input.get('value')
                if name and value:
                    if name not in tmid_groups:
                        tmid_groups[name] = []
                    tmid_groups[name].append({
                        'value': value,
                        'input': tmid_input
                    })
            
            # 为每个问卷题目选择第一个选项（A选项）
            for group_name, options in tmid_groups.items():
                if options:
                    # 选择第一个选项（A选项）
                    form_data[group_name] = options[0]['value']
                    print(f"  - 问卷题目 {group_name}: 选择A选项")
            
            # 4. 设置提交状态
            form_data['issubmit'] = '1'  # 设置为提交状态
            
            # 5. 其他意见建议（可选，留空）
            form_data['jynr'] = ''
            
            # 提交表单
            submit_url = "http://jw.cupk.edu.cn/jsxsd/xspj/xspj_save.do"
            
            print(f"正在提交评教表单...")
            print(f"提交的数据项数量: {len(form_data)}")
            
            submit_response = self.session.post(
                submit_url, 
                data=form_data, 
                headers=self.headers, 
                timeout=15
            )
            submit_response.raise_for_status()
            
            # 检查提交结果
            if submit_response.status_code == 200:
                print(f"✅ 课程 {course_info['course_name']} 评教提交成功！")
                
                # 检查响应内容是否包含成功信息
                if "成功" in submit_response.text or "保存" in submit_response.text:
                    print(f"   评教数据已保存到系统")
                elif "错误" in submit_response.text or "失败" in submit_response.text:
                    print(f"   ⚠️ 可能存在问题，请检查响应内容")
                
                return True
            else:
                print(f"❌ 提交失败，HTTP状态码: {submit_response.status_code}")
                return False
                
        except requests.exceptions.Timeout:
            print(f"访问课程 {course_info['course_name']} 评教页面超时。")
            return False
        except requests.exceptions.RequestException as e:
            print(f"访问课程 {course_info['course_name']} 评教页面时发生网络错误: {str(e)}")
            return False
        except Exception as e:
            print(f"处理课程 {course_info['course_name']} 评教时发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def auto_evaluate_courses(self, evaluation_url):
        """自动评教主流程"""
        print("开始自动评教流程...")
        
        # 1. 获取课程列表
        html_content = self.get_course_list(evaluation_url)
        if not html_content:
            print("无法获取课程列表。")
            return
        
        # 2. 解析课程信息
        courses = self.parse_course_list(html_content)
        if not courses:
            print("未找到课程信息。")
            return
        
        print(f"找到 {len(courses)} 门课程。")
        
        # 3. 显示所有课程信息
        print("\n=== 课程列表 ===")
        for course in courses:
            print(f"课程: {course['course_name']} - 教师: {course['teacher']} - 已评: {course['is_evaluated']} - 已提交: {course['is_submitted']}")
        
        # 4. 查找未提交的评教
        unevaluated_courses = self.find_unevaluated_courses(courses)
        
        if not unevaluated_courses:
            print("\n所有课程评教均已提交，无需进行评教操作。")
            return
        
        print(f"\n找到 {len(unevaluated_courses)} 门课程需要进行评教：")
        for course in unevaluated_courses:
            print(f"- {course['course_name']} (教师: {course['teacher']})")
        
        # 5. 对未提交的课程进行评教
        success_count = 0
        for course in unevaluated_courses:
            print(f"\n正在处理课程: {course['course_name']}")
            if self.perform_evaluation(course):
                success_count += 1
            else:
                print(f"课程 {course['course_name']} 评教失败。")
        
        print(f"\n评教完成！成功处理 {success_count}/{len(unevaluated_courses)} 门课程。")

def main():
    # 使用环境变量或默认值
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

    evaluation_system = EvaluationSystem()
    
    print(f"尝试使用学号 {username} 登录教务系统...")
    if evaluation_system.login(username, password):
        print("\n登录成功，开始访问评教页面...")
        
        # 访问评教页面
        html_content = evaluation_system.get_evaluation_page()
        
        if html_content:
            print("\n成功获取评教页面内容。")
            
            # 解析并显示评教链接
            evaluation_links = evaluation_system.parse_evaluation_links(html_content)
            evaluation_system.display_evaluation_info(evaluation_links)
            
            # 查找评教链接并自动进行评教
            soup = BeautifulSoup(html_content, 'html.parser')
            target_link = soup.find('a', href=re.compile(r'/jsxsd/xspj/xspj_list\.do.*'))
            if target_link:
                print(f"\n=== 找到的评教链接 ===")
                print(f"链接HTML: {target_link}")
                print(f"链接URL: {target_link.get('href')}")
                full_url = f"http://jw.cupk.edu.cn{target_link.get('href')}"
                print(f"完整URL: {full_url}")
                
                # 开始自动评教流程
                print("\n" + "="*50)
                print("开始自动评教流程...")
                print("="*50)
                evaluation_system.auto_evaluate_courses(full_url)
            else:
                print("\n未找到评教链接，无法进行自动评教。")
                
            # 如果需要显示完整的HTML响应，可以取消注释下面的代码
            # print("\n=== 评教页面完整响应 ===")
            # print(html_content)
                
        else:
            print("\n未能获取评教页面内容。")
    else:
        print("\n登录失败，无法继续访问评教页面。请检查账号密码及网络连接。")

if __name__ == "__main__":
    main()