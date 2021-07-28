from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver import ChromeOptions, Chrome
import time
from fake_useragent import UserAgent
from alive_progress import alive_bar
from settings import TEAM_NAMES, CHROMEDRIVER_PATH
import pandas as pd
from datetime import date
import glob

class TestTop30():
  def __init__(self, team, org):
    self.team = team
    self.org = org
    opts = ChromeOptions()
    opts.add_experimental_option("detach", True)
    ua = UserAgent()
    opts.add_argument(f'user-agent={ua.random}')
    opts.add_argument('--headless')
    opts.add_argument('log-level=3')
    self.driver = webdriver.Chrome(executable_path=CHROMEDRIVER_PATH, options=opts)
  
  def teardown_method(self):
    self.driver.quit()
  
  def test_top30(self):
    self.driver.get("https://www.mlb.com/prospects/2021/")
    # self.driver.set_window_size(1920, 1080)
    # self.driver.find_element(By.CSS_SELECTOR, ".nav-tab-dropdown__item:nth-child(2) .dropdown__select").click()
    # dropdown = self.driver.find_element(By.CSS_SELECTOR, ".nav-tab-dropdown__item:nth-child(2) .dropdown__select")
    dropdown = self.driver.find_element(By.CSS_SELECTOR, ".nav-tab-dropdown__item:nth-child(2)")
    dropdown.find_element(By.XPATH, f"//option[. = '{self.team}']").click()
    self.driver.implicitly_wait(5)
    WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((
        By.CSS_SELECTOR, ".load-more__button"))).click()
    # while True:
    #   try:
    #     WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((
    #       By.CSS_SELECTOR, ".load-more__button"))).click()
    #     break
    #   except:
    #     pass
    # self.driver.find_element(By.CSS_SELECTOR, ".load-more__button").click()

  def frame_to_excel(self):
    today = date.today().strftime('%m-%d')
    with pd.ExcelWriter(f'Teams4\\{self.team.replace(" ", "")}-{today}.xlsx', engine='openpyxl') as writer:
      self.df.to_excel(writer, sheet_name=f'{self.team}', index=False)
      writer.save()
  
  def extract_players(self):
    self.df = pd.read_html(self.driver.page_source)[0]
    # self.players = self.df['Player'].values
    teams = []
    org = [self.org] * 30
    players = []
    handles = []
    drafted = []
    with alive_bar(30, title=self.team,length=30, bar='checks', spinner='dots_waves') as bar:
      for num in range(1, 31):
        player = self.df['Player'][num-1]
        # print(f'{player}')
        # bar.text(cprint(f'{player}', 'green'))
        bar.text(f'{player}')
        team = None
        while not team:
          try:
            self.driver.implicitly_wait(1)
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((
              By.CSS_SELECTOR, f".sc-VigVT:nth-child({str(num)}) .prospect-headshot__name"))).click()
            # self.driver.find_element(By.CSS_SELECTOR, f".sc-VigVT:nth-child({str(num)}) .prospect-headshot__name").click()
            # self.driver.find_element(By.CSS_SELECTOR, f".sc-VigVT:nth-child(2) .prospect-headshot__name").click()
            element = WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((
              By.CSS_SELECTOR, "div.top-card__bottom-left-container__meta"
              )))
            
            try:
              twitter = self.driver.find_element_by_css_selector('div.bio-tab__statValue a').text
              handles.append(twitter)
            except:
              handles.append('None')
              pass

            try:
              # draft = self.driver.find_element_by_css_selector('div.bio-tab__statValue:nth-child(5)')
              draft = self.driver.find_element_by_xpath('//*[@id="root"]/div/div/div[3]/div[2]/div[2]/div/div[3]/div/ul[1]/li[6]/div[2]').text
              draft = draft[:-5]
              drafted.append(draft)

            except:
              drafted.append('None')
              pass

            while True:
              try:
                team = element.text.split(',')[1]
              except Exception as e:
                print(e)
                team = 'None'
              break

            if player not in players:
              teams.append(team)
              players.append(player)
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((
              By.CSS_SELECTOR, "button.drawer__close-container"))).click()

          except Exception as e:
            if e == KeyboardInterrupt:
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
    # self.df.insert(4, 'ORG', org)

    print(f'\n{self.df.to_string(index=False)}')

def master_combine():
  files = glob.glob('Teams3/*')
  today = date.today().strftime('%m-%d')

  all_data = pd.DataFrame()
  for file in files:
      df = pd.read_excel(file, ignore_index=True)
      all_data = all_data.append(df, ignore_index=True)

  with pd.ExcelWriter(f'Teams3/RecruitingMaster-{today}.xlsx', engine='openpyxl', mode='w') as writer:
      all_data.to_excel(writer, sheet_name='Master', index=False)

def main():
  for team, org in TEAM_NAMES.items():
    with alive_bar(2) as bar:
      scrape = TestTop30(team, org)
      bar.text('[+] Loading Team Page...')
      scrape.test_top30()
      bar()
      scrape.extract_players()
      print(scrape.df)
      scrape.frame_to_excel()
      scrape.teardown_method()
  master_combine()
  
main()