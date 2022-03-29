from doctest import master
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver import ChromeOptions, Chrome
from settings import TEAM_NAMES, CHROMEDRIVER_PATH
import pandas as pd
from datetime import date
import glob
import argparse
import os
import re
from concurrent.futures import ThreadPoolExecutor

# Initialize the team and organization to be scraped
class TestTop30():
  def __init__(self, team: str, org: str) -> None:
    """
    Initializes the correct variables corresponding to team and organization.
    """
    self.team = team
    self.org = org
    opts = ChromeOptions()
    # opts.add_experimental_option("detach", True)
    opts.add_argument('--headless')
    # opts.add_argument('log-level=3')
    self.driver = Chrome(executable_path=CHROMEDRIVER_PATH, options=opts)

  def test_top30(self) -> None:
    """
    Gets the URL below and finds the correct team we want to scrape. 
    """
    self.driver.get("https://www.mlb.com/prospects/")
    dropdown = self.driver.find_element(By.CSS_SELECTOR, ".nav-tab-dropdown__item:nth-child(2)")
    dropdown.find_element(By.XPATH, f"//option[. = '{self.team}']").click()
    self.driver.implicitly_wait(5)
    WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((
        By.CSS_SELECTOR, "[data-testid=load-more-button]"))).click()
    
  def extract_players(self) -> None:
    """
    Extracts all the individual data frame each players Pipeline page and writes to a dataframe.
    """
    self.df = pd.read_html(self.driver.page_source)[0]
    teams = []
    org = [self.org] * 30
    players = []
    handles = []
    drafted = []

    for num in range(1, 31):
      player = self.df['Player'][num-1]
      team = None
      print(player)
      while not team:
        self.driver.implicitly_wait(3)
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((
          By.CSS_SELECTOR, f".sc-VigVT:nth-child({str(num)}) .prospect-headshot__name"))).click()
        element = WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((
          By.CSS_SELECTOR, "div.top-card__bottom-left-container__meta"
          )))
        
        # Grab twitter handle
        try:
          print('Trying to grab twitter handle...')
          twitter = self.driver.find_element_by_css_selector('.Styles__BioTabContainer-sc-1vyfrup-0 li:nth-child(9) div a').text
          handles.append(twitter)
          print(twitter)

        except Exception as e:
          print(e)
          handles.append('None')
          pass

        # Grab draft year
        try:
          print('Trying to grab draft year...')
          draft = self.driver.find_element_by_css_selector('.Styles__BioTabContainer-sc-1vyfrup-0 li:nth-child(6) div.bio-tab__statValue').text
          draft = draft.split('-', 1)[0]
          if re.search(r'\(\d+\)', draft):
            draft = draft.split('(')[0].rstrip()
          drafted.append(draft.rstrip())
          print(draft)

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

        while True:
          try:
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((
              By.CSS_SELECTOR, "button.drawer__close-container"))).click()
            break
          except:
            continue

        # bar() 

    self.df['ORG'] = org
    self.df['Team'] = teams
    self.df['Handle'] = handles
    self.df['Draft'] = drafted

    print(f'\n{self.df.to_string(index=False)}')

  def frame_to_excel(self, folder: str) -> None:
    """
    Write the dataframe to an Excel file.
    """
    today = date.today().strftime('%m-%d')
    with pd.ExcelWriter(f'{folder}\\{self.team.replace(" ", "")}-{today}.xlsx', engine='openpyxl') as writer:
      self.df.to_excel(writer, sheet_name=f'{self.team}', index=False)
      writer.save()

  def teardown_method(self):
    self.driver.quit()

def master_combine(folder:str) -> None:
  """
  Parse through all the dataframes in each individual excel file and write them to one master file
  """
  files = glob.glob(f'{folder}/*')
  today = date.today().strftime('%m-%d')

  all_data = pd.DataFrame()
  for file in files:
      df = pd.read_excel(file, index_col=None)
      all_data = all_data.append(df, ignore_index=True)

  with pd.ExcelWriter(f'{folder}\\RecruitingMaster-{today}.xlsx', engine='openpyxl', mode='w') as writer:
      all_data.to_excel(writer, sheet_name='Master', index=False)

def main() -> None:
  """
  Start of the program that will parse arguments and start the threadpool
  """
  # Create the programs arguments
  parser = argparse.ArgumentParser(description='Enter the folder name you want to store the excel files')
  parser.add_argument('-f', '--folder', help="Enter the folder you want to store the excel files", required=True)

  # Had to make this global to use in the threading function
  global args
  args = parser.parse_args()

  if "/" in args.folder:
    args.folder.replace('/', '')

  if not os.path.isdir(args.folder):
    os.mkdir(args.folder)
   
  # Thread through the names in settings and grab them all, 5 at a time
  with ThreadPoolExecutor(max_workers=5) as executor:
    for team, org in TEAM_NAMES.items():
      executor.submit(thread, team, org)
    
  # Combine all the files into one
  master_combine(args.folder)

def thread(team: str, org: str) -> None:
  """ 
  Goes through each of the teams and grabs the players stats, info, etc. and creates a dataframe. Then writes the dataframe
  to Excel.
  """
  while True:
    scrape = TestTop30(team, org)

    # This errors out a good amount so just start over on the team if it does
    try:
      scrape.test_top30()
      scrape.extract_players()
      print(scrape.df)

    except Exception as e:
      print(e)
      scrape.teardown_method()
      del scrape
      continue

    # Write the dataframe to an excel file
    scrape.frame_to_excel(args.folder)

    # Teardown afterwards
    scrape.teardown_method()
    del scrape
    break
  
if __name__ == "__main__":
  main()