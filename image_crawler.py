import customtkinter as ctk
import os
import requests
import time
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, TimeoutException

class ImageCrawlerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Google Image Crawler")
        self.geometry("400x350")

        self.grid_columnconfigure(1, weight=1)

        # UI Elements
        self.keyword_label = ctk.CTkLabel(self, text="Keyword:")
        self.keyword_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")
        self.keyword_entry = ctk.CTkEntry(self, placeholder_text="e.g., cats")
        self.keyword_entry.grid(row=0, column=1, padx=20, pady=10, sticky="ew")

        self.num_images_label = ctk.CTkLabel(self, text="Number of Images:")
        self.num_images_label.grid(row=1, column=0, padx=20, pady=10, sticky="w")
        self.num_images_entry = ctk.CTkEntry(self, placeholder_text="e.g., 10")
        self.num_images_entry.grid(row=1, column=1, padx=20, pady=10, sticky="ew")

        self.start_button = ctk.CTkButton(self, text="Start Crawling", command=self.start_crawling_thread)
        self.start_button.grid(row=2, column=0, columnspan=2, padx=20, pady=10)

        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=3, column=0, columnspan=2, padx=20, pady=10, sticky="ew")

        self.status_label = ctk.CTkLabel(self, text="Status: Ready")
        self.status_label.grid(row=4, column=0, columnspan=2, padx=20, pady=10)

    def start_crawling_thread(self):
        keyword = self.keyword_entry.get()
        num_images_str = self.num_images_entry.get()

        if not keyword:
            self.update_gui(text="Status: Please enter a keyword.")
            return
        if not num_images_str.isdigit() or int(num_images_str) <= 0:
            self.update_gui(text="Status: Please enter a valid number of images.")
            return

        num_images = int(num_images_str)

        self.start_button.configure(state="disabled")
        crawl_thread = threading.Thread(target=self.crawl_images, args=(keyword, num_images))
        crawl_thread.start()

    def update_gui(self, text=None, progress=None):
        if text:
            self.status_label.configure(text=text)
        if progress is not None:
            self.progress_bar.set(progress)

    def crawl_images(self, keyword, num_images):
        try:
            self.after(0, self.update_gui, "Status: Starting...")
            self.after(0, lambda: self.progress_bar.set(0))

            options = webdriver.ChromeOptions()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            driver = webdriver.Chrome(options=options)

            if not os.path.exists(keyword):
                os.makedirs(keyword)

            driver.get(f"https://www.google.com/search?q={keyword}&tbm=isch")

            image_urls = set()
            last_height = driver.execute_script("return document.body.scrollHeight")

            self.after(0, self.update_gui, "Status: Searching for images...")

            while len(image_urls) < num_images:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)

                thumbnails = driver.find_elements(By.CSS_SELECTOR, "img.rg_i")

                for img in thumbnails[len(image_urls):]:
                    try:
                        driver.execute_script("arguments[0].click();", img)
                        time.sleep(1)

                        wait = WebDriverWait(driver, 10)
                        high_res_images = wait.until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'img.sFlh5c'))
                        )

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
                        continue
                    except Exception as e:
                        print(f"Error collecting image URL: {e}")

                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    try:
                        more_results_button = driver.find_element(By.CSS_SELECTOR, "input.mye4qd")
                        if more_results_button.is_displayed():
                            driver.execute_script("arguments[0].click();", more_results_button)
                            time.sleep(2)
                        else:
                            break
                    except NoSuchElementException:
                        break
                last_height = new_height

            # Download images
            downloaded_count = 0
            for i, url in enumerate(list(image_urls)[:num_images]):
                try:
                    response = requests.get(url, stream=True, timeout=10)
                    response.raise_for_status()

                    content_type = response.headers.get('content-type')
                    extension = ".jpg"
                    if content_type:
                        if 'jpeg' in content_type.lower(): extension = ".jpg"
                        elif 'png' in content_type.lower(): extension = ".png"
                        elif 'gif' in content_type.lower(): extension = ".gif"

                    filepath = f"{keyword}/image_{i+1}{extension}"
                    with open(filepath, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)

                    downloaded_count += 1
                    progress = downloaded_count / num_images
                    self.after(0, self.update_gui, f"Status: Downloading {downloaded_count}/{num_images}...", progress)
                except Exception as e:
                    print(f"Could not download {url}. Error: {e}")

            driver.quit()
            self.after(0, self.update_gui, f"Status: Download complete! {downloaded_count} images saved.")

        except Exception as e:
            self.after(0, self.update_gui, f"Status: An error occurred: {e}")
        finally:
            self.after(0, lambda: self.start_button.configure(state="normal"))

if __name__ == "__main__":
    app = ImageCrawlerApp()
    app.mainloop()
