import customtkinter as ctk
import os
import requests
import time
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException

class ImageCrawlerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Google Image Crawler")
        self.geometry("400x350")

        self.grid_columnconfigure(1, weight=1)

        # Keyword Entry
        self.keyword_label = ctk.CTkLabel(self, text="Keyword:")
        self.keyword_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")
        self.keyword_entry = ctk.CTkEntry(self, placeholder_text="e.g., cats")
        self.keyword_entry.grid(row=0, column=1, padx=20, pady=10, sticky="ew")

        # Number of Images Entry
        self.num_images_label = ctk.CTkLabel(self, text="Number of Images:")
        self.num_images_label.grid(row=1, column=0, padx=20, pady=10, sticky="w")
        self.num_images_entry = ctk.CTkEntry(self, placeholder_text="e.g., 10")
        self.num_images_entry.grid(row=1, column=1, padx=20, pady=10, sticky="ew")

        # Start Button
        self.start_button = ctk.CTkButton(self, text="Start Crawling", command=self.start_crawling_thread)
        self.start_button.grid(row=2, column=0, columnspan=2, padx=20, pady=10)

        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=3, column=0, columnspan=2, padx=20, pady=10, sticky="ew")

        # Status Label
        self.status_label = ctk.CTkLabel(self, text="Status: Ready")
        self.status_label.grid(row=4, column=0, columnspan=2, padx=20, pady=10)

    def start_crawling_thread(self):
        keyword = self.keyword_entry.get()
        num_images_str = self.num_images_entry.get()

        if not keyword:
            self.status_label.configure(text="Status: Please enter a keyword.")
            return
        if not num_images_str.isdigit() or int(num_images_str) <= 0:
            self.status_label.configure(text="Status: Please enter a valid number of images.")
            return

        num_images = int(num_images_str)

        # Disable button during crawling
        self.start_button.configure(state="disabled")

        # Run crawling in a separate thread
        crawl_thread = threading.Thread(target=self.crawl_images, args=(keyword, num_images))
        crawl_thread.start()

    def crawl_images(self, keyword, num_images):
        try:
            self.after(0, lambda: self.status_label.configure(text="Status: Starting..."))
            self.after(0, lambda: self.progress_bar.set(0))

            # Setup WebDriver using Selenium Manager
            options = webdriver.ChromeOptions()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            driver = webdriver.Chrome(options=options)

            # Create directory to save images
            if not os.path.exists(keyword):
                os.makedirs(keyword)

            # Go to Google Images
            driver.get(f"https://www.google.com/search?q={keyword}&tbm=isch")


            # Scroll to load more images
            last_height = driver.execute_script("return document.body.scrollHeight")
            image_urls = set()

            while len(image_urls) < num_images:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    try:
                        # Click "Show more results" button if it exists
                        more_results_button = driver.find_element(By.CSS_SELECTOR, ".mye4qd")
                        if more_results_button:
                            more_results_button.click()
                            time.sleep(2)
                    except (NoSuchElementException, ElementClickInterceptedException):
                        # If no more results button, break
                        break
                last_height = new_height

                # Get image thumbnails
                thumbnails = driver.find_elements(By.CSS_SELECTOR, "img.Q4LuWd")

                for img in thumbnails[len(image_urls):num_images]:
                    try:
                        img.click()
                        time.sleep(1)
                        # Extract image source from the larger preview
                        images = driver.find_elements(By.CSS_SELECTOR, 'img.sFlh5c.pT0Scc.iPVvYb')
                        for image in images:
                            src = image.get_attribute('src')
                            if src and ('http' in src) and src not in image_urls:
                                 image_urls.add(src)
                                 if len(image_urls) >= num_images:
                                     break
                        if len(image_urls) >= num_images:
                            break
                    except Exception as e:
                        print(f"Error clicking thumbnail: {e}")
                        continue

            # Download images
            downloaded_count = 0
            for i, url in enumerate(list(image_urls)[:num_images]):
                try:
                    response = requests.get(url, stream=True, timeout=10)
                    response.raise_for_status()

                    # Try to determine file extension
                    content_type = response.headers.get('content-type')
                    extension = ".jpg" # default
                    if content_type:
                        if 'jpeg' in content_type.lower():
                            extension = ".jpg"
                        elif 'png' in content_type.lower():
                            extension = ".png"
                        elif 'gif' in content_type.lower():
                            extension = ".gif"

                    filepath = f"{keyword}/image_{i+1}{extension}"
                    with open(filepath, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)

                    downloaded_count += 1
                    # Update progress bar
                    progress = downloaded_count / num_images
                    status_text = f"Status: Downloading image {downloaded_count}/{num_images}"
                    self.after(0, lambda p=progress: self.progress_bar.set(p))
                    self.after(0, lambda s=status_text: self.status_label.configure(text=s))


                except Exception as e:
                    print(f"Could not download {url}. Error: {e}")

            driver.quit()
            status_text = f"Status: Download complete! {downloaded_count} images saved."
            self.after(0, lambda: self.status_label.configure(text=status_text))

        except Exception as e:
            self.after(0, lambda e=e: self.status_label.configure(text=f"Status: An error occurred: {e}"))
        finally:
            # Re-enable button
            self.after(0, lambda: self.start_button.configure(state="normal"))


if __name__ == "__main__":
    app = ImageCrawlerApp()
    app.mainloop()
