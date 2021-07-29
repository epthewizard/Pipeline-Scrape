from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver import ChromeOptions, Chrome
import time
from alive_progress import alive_bar
from settings import TEAM_NAMES, CHROMEDRIVER_PATH
import pandas as pd
from datetime import date
import glob
import argparse
import os

# Initialize the team and organization to be scraped
class TestTop30():
  def __init__(self, team, org):
    self.team = team
    self.org = org
    opts = ChromeOptions()
    opts.add_experimental_option("detach", True)
    opts.add_argument('--headless')
    opts.add_argument('log-level=3')
    self.driver = Chrome(executable_path=CHROMEDRIVER_PATH, options=opts)

  # Go to the scraped teams top30 page and drop down the entire list  
  def test_top30(self):
    self.driver.get("https://www.mlb.com/prospects/2021/")
    dropdown = self.driver.find_element(By.CSS_SELECTOR, ".nav-tab-dropdown__item:nth-child(2)")
    dropdown.find_element(By.XPATH, f"//option[. = '{self.team}']").click()
    self.driver.implicitly_wait(5)
    WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((
        By.CSS_SELECTOR, ".load-more__button"))).click()

  # Scrape the list of players and create pandas dataframe for other information to be added
  def extract_players(self):
    # Grab the basic information from the page source
    self.df = pd.read_html(self.driver.page_source)[0]
    teams = []
    org = [self.org] * 30
    players = []
    handles = []
    drafted = []

    with alive_bar(30, title=self.team,length=30, bar='checks', spinner='dots_waves') as bar:
      for num in range(1, 31):
        player = self.df['Player'][num-1]
        bar.text(f'{player}')
        team = None
        while not team:
          try:
            self.driver.implicitly_wait(1)
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((
              By.CSS_SELECTOR, f".sc-VigVT:nth-child({str(num)}) .prospect-headshot__name"))).click()
            element = WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((
              By.CSS_SELECTOR, "div.top-card__bottom-left-container__meta"
              )))
            
            # Grab twitter handle
            try:
              twitter = self.driver.find_element_by_css_selector('div.bio-tab__statValue a').text
              handles.append(twitter)
            except:
              handles.append('None')
              pass

            # Grab draft year
            try:
              draft = self.driver.find_element_by_xpath('//*[@id="root"]/div/div/div[3]/div[2]/div[2]/div/div[3]/div/ul[1]/li[6]/div[2]').text
              draft = draft[:-5]
              drafted.append(draft)

            except:
              drafted.append('None')
              pass

            while True:
              try:
                team = element.text.split(',')[1].lstrip()
              except Exception as e:
                print(e)
                team = 'None'
              break

            if player not in players:
              teams.append(team)
              players.append(player)
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((
              By.CSS_SELECTOR, "button.drawer__close-container"))).click()

          except KeyboardInterrupt:
            self.teardown_method()
            time.sleep(2)
            team = None
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((
              By.CSS_SELECTOR, "button.drawer__close-container"))).click()
        bar() 

    self.df['ORG'] = org
    self.df['Team'] = teams
    self.df['Handle'] = handles
    self.df['Draft'] = drafted

    print(f'\n{self.df.to_string(index=False)}')

  def frame_to_excel(self, folder):
    today = date.today().strftime('%m-%d')
    with pd.ExcelWriter(f'{folder}\\{self.team.replace(" ", "")}-{today}.xlsx', engine='openpyxl') as writer:
      self.df.to_excel(writer, sheet_name=f'{self.team}', index=False)
      writer.save()

  def teardown_method(self):
    self.driver.quit()

def master_combine(folder):
  files = glob.glob(f'{folder}/*')
  today = date.today().strftime('%m-%d')

  all_data = pd.DataFrame()
  for file in files:
      df = pd.read_excel(file, ignore_index=True)
      all_data = all_data.append(df, ignore_index=True)

  with pd.ExcelWriter(f'{folder}\\RecruitingMaster-{today}.xlsx', engine='openpyxl', mode='w') as writer:
      all_data.to_excel(writer, sheet_name='Master', index=False)

def main():
  parser = argparse.ArgumentParser(description='Enter the folder name you want to store the excel files')
  parser.add_argument('-f', '--folder', help="Enter the folder you want to store the excel files", required=True)
  args = parser.parse_args()

  if "/" in args.folder:
    args.folder.replace('/', '')

  if not os.path.isdir(args.folder):
    os.mkdir(args.folder)

  for team, org in TEAM_NAMES.items():
    with alive_bar(2) as bar:
      scrape = TestTop30(team, org)
      bar.text('[+] Loading Team Page...')
      scrape.test_top30()
      bar()
      scrape.extract_players()
      print(scrape.df)
      scrape.frame_to_excel(args.folder)
      scrape.teardown_method()
  master_combine(args.folder)
  
if __name__ == "__main__":
  main()