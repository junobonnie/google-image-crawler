# 필요한 라이브러리들을 가져옵니다.
import customtkinter as ctk  # GUI를 위한 customtkinter 라이브러리
import os  # 운영체제와 상호작용하기 위한 라이브러리 (예: 폴더 생성)
import requests  # HTTP 요청을 보내기 위한 라이브러리 (이미지 다운로드)
import time  # 시간 관련 기능을 위한 라이브러리 (예: 일시 정지)
import threading  # 병렬 처리를 위한 라이브러리 (GUI와 크롤링 분리)
from selenium import webdriver  # 웹 브라우저 자동화를 위한 Selenium
from selenium.webdriver.common.by import By  # 요소를 찾기 위한 방법 지정
from selenium.webdriver.common.keys import Keys  # 키보드 입력을 위한 라이브...
from selenium.webdriver.support.ui import WebDriverWait  # 특정 조건이 충족될 때까지 기다리기 위함
from selenium.webdriver.support import expected_conditions as EC  # WebDriverWait에 대한 예상 조건
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, TimeoutException  # 발생할 수 있는 예외 처리

# ImageCrawlerApp 클래스는 ctk.CTk를 상속받아 GUI 애플리케이션의 메인 창을 생성합니다.
class ImageCrawlerApp(ctk.CTk):
    def __init__(self):
        super().__init__()  # 부모 클래스(ctk.CTk)의 생성자를 호출합니다.

        self.title("Google Image Crawler")  # 창의 제목을 설정합니다.
        self.geometry("400x350")  # 창의 크기를 설정합니다.

        self.grid_columnconfigure(1, weight=1)  # 두 번째 열이 창 크기 조절에 따라 확장되도록 설정합니다.

        # --- UI 요소 생성 ---
        # 키워드 입력 필드
        self.keyword_label = ctk.CTkLabel(self, text="Keyword:")
        self.keyword_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")
        self.keyword_entry = ctk.CTkEntry(self, placeholder_text="e.g., cats")
        self.keyword_entry.grid(row=0, column=1, padx=20, pady=10, sticky="ew")

        # 이미지 개수 입력 필드
        self.num_images_label = ctk.CTkLabel(self, text="Number of Images:")
        self.num_images_label.grid(row=1, column=0, padx=20, pady=10, sticky="w")
        self.num_images_entry = ctk.CTkEntry(self, placeholder_text="e.g., 10")
        self.num_images_entry.grid(row=1, column=1, padx=20, pady=10, sticky="ew")

        # 크롤링 시작 버튼
        self.start_button = ctk.CTkButton(self, text="Start Crawling", command=self.start_crawling_thread)
        self.start_button.grid(row=2, column=0, columnspan=2, padx=20, pady=10)

        # 진행률 표시줄
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=3, column=0, columnspan=2, padx=20, pady=10, sticky="ew")

        # 상태 메시지 레이블
        self.status_label = ctk.CTkLabel(self, text="Status: Ready")
        self.status_label.grid(row=4, column=0, columnspan=2, padx=20, pady=10)

    # 크롤링 시작 버튼을 눌렀을 때 호출되는 메서드
    def start_crawling_thread(self):
        keyword = self.keyword_entry.get()  # 키워드 입력 필드에서 텍스트를 가져옵니다.
        num_images_str = self.num_images_entry.get()  # 이미지 개수 입력 필드에서 텍스트를 가져옵니다.

        # 입력 값 유효성 검사
        if not keyword:
            self.update_gui(text="Status: Please enter a keyword.")
            return
        if not num_images_str.isdigit() or int(num_images_str) <= 0:
            self.update_gui(text="Status: Please enter a valid number of images.")
            return

        num_images = int(num_images_str)  # 이미지 개수를 정수로 변환합니다.

        self.start_button.configure(state="disabled")  # 크롤링 중에는 버튼을 비활성화합니다.
        # 크롤링 작업을 별도의 스레드에서 실행하여 GUI가 멈추는 것을 방지합니다.
        crawl_thread = threading.Thread(target=self.crawl_images, args=(keyword, num_images))
        crawl_thread.start()

    # GUI를 업데이트하는 메서드 (스레드 안전)
    def update_gui(self, text=None, progress=None):
        if text:
            self.status_label.configure(text=text)  # 상태 메시지를 업데이트합니다.
        if progress is not None:
            self.progress_bar.set(progress)  # 진행률 표시줄을 업데이트합니다.

    # 실제 이미지 크롤링을 수행하는 메서드
    def crawl_images(self, keyword, num_images):
        try:
            # self.after를 사용하여 메인 GUI 스레드에서 GUI 업데이트를 예약합니다.
            self.after(0, self.update_gui, "Status: Starting...")
            self.after(0, lambda: self.progress_bar.set(0))

            # Selenium WebDriver 설정
            options = webdriver.ChromeOptions()
            options.add_argument("--headless")  # 브라우저 창을 띄우지 않고 백그라운드에서 실행합니다.
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            driver = webdriver.Chrome(options=options)

            # 키워드 이름으로 폴더가 없으면 생성합니다.
            if not os.path.exists(keyword):
                os.makedirs(keyword)

            # Google 이미지 검색 페이지로 이동합니다.
            driver.get(f"https://www.google.com/search?q={keyword}&tbm=isch")

            image_urls = set()  # 중복된 이미지 URL을 방지하기 위해 집합(set)을 사용합니다.
            last_height = driver.execute_script("return document.body.scrollHeight")  # 현재 페이지 높이를 가져옵니다.

            self.after(0, self.update_gui, "Status: Searching for images...")

            # 원하는 개수의 이미지 URL을 수집할 때까지 반복합니다.
            while len(image_urls) < num_images:
                # 페이지 맨 아래로 스크롤하여 더 많은 이미지를 로드합니다.
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # 이미지가 로드될 때까지 잠시 기다립니다.

                # 썸네일 이미지 요소를 모두 찾습니다.
                thumbnails = driver.find_elements(By.CSS_SELECTOR, "img.rg_i")

                # 새로 로드된 썸네일 이미지만큼 반복합니다.
                for img in thumbnails[len(image_urls):]:
                    try:
                        # 썸네일 이미지를 클릭하여 원본 이미지를 표시합니다.
                        driver.execute_script("arguments[0].click();", img)
                        time.sleep(1)

                        # 원본 이미지가 로드될 때까지 최대 10초간 기다립니다.
                        wait = WebDriverWait(driver, 10)
                        high_res_images = wait.until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'img.sFlh5c'))
                        )

                        # 고해상도 이미지 URL을 추출합니다.
                        for high_res_img in high_res_images:
                            src = high_res_img.get_attribute("src")
                            if src and src.startswith('http') and src not in image_urls:
                                image_urls.add(src)
                                self.after(0, self.update_gui, f"Status: Found {len(image_urls)}/{num_images} images...")
                                if len(image_urls) >= num_images:
                                    break
                        if len(image_urls) >= num_images:
                            break

                    except (ElementClickInterceptedException, TimeoutException):
                        # 클릭이 가로채지거나 시간 초과 예외가 발생하면 다음 썸네일로 넘어갑니다.
                        continue
                    except Exception as e:
                        print(f"Error collecting image URL: {e}")

                # 스크롤 후 페이지 높이를 다시 확인합니다.
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    # 페이지 높이에 변화가 없으면 "결과 더보기" 버튼을 찾아 클릭합니다.
                    try:
                        more_results_button = driver.find_element(By.CSS_SELECTOR, "input.mye4qd")
                        if more_results_button.is_displayed():
                            driver.execute_script("arguments[0].click();", more_results_button)
                            time.sleep(2)
                        else:
                            # 더 이상 로드할 이미지가 없으면 루프를 종료합니다.
                            break
                    except NoSuchElementException:
                        # "결과 더보기" 버튼이 없으면 루프를 종료합니다.
                        break
                last_height = new_height

            # --- 이미지 다운로드 ---
            downloaded_count = 0
            for i, url in enumerate(list(image_urls)[:num_images]):
                try:
                    # 이미지 URL에 GET 요청을 보냅니다.
                    response = requests.get(url, stream=True, timeout=10)
                    response.raise_for_status()  # 요청이 실패하면 예외를 발생시킵니다.

                    # Content-Type 헤더를 확인하여 파일 확장자를 결정합니다.
                    content_type = response.headers.get('content-type')
                    extension = ".jpg"
                    if content_type:
                        if 'jpeg' in content_type.lower(): extension = ".jpg"
                        elif 'png' in content_type.lower(): extension = ".png"
                        elif 'gif' in content_type.lower(): extension = ".gif"

                    # 이미지 파일을 저장합니다.
                    filepath = f"{keyword}/image_{i+1}{extension}"
                    with open(filepath, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)

                    downloaded_count += 1
                    progress = downloaded_count / num_images
                    self.after(0, self.update_gui, f"Status: Downloading {downloaded_count}/{num_images}...", progress)
                except Exception as e:
                    print(f"Could not download {url}. Error: {e}")

            driver.quit()  # 웹 드라이버를 종료합니다.
            self.after(0, self.update_gui, f"Status: Download complete! {downloaded_count} images saved.")

        except Exception as e:
            self.after(0, self.update_gui, f"Status: An error occurred: {e}")
        finally:
            # 크롤링이 성공하든 실패하든 항상 시작 버튼을 다시 활성화합니다.
            self.after(0, lambda: self.start_button.configure(state="normal"))

# 이 스크립트가 직접 실행될 때만 아래 코드를 실행합니다.
if __name__ == "__main__":
    app = ImageCrawlerApp()  # ImageCrawlerApp 인스턴스를 생성합니다.
    app.mainloop()  # GUI 애플리케이션의 이벤트 루프를 시작합니다.
