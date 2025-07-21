# **HLTV Demo Downloader**
CLI tool that downloads HLTV demos in bulk.

It only works with pages that have "stats" and "matches" in the url, for example [this player page](https://www.hltv.org/stats/players/matches/11816/ropz) or [this team page](https://www.hltv.org/stats/teams/matches/9565/vitality).

Pages that contain "result" in the url, for example [this team page](https://www.hltv.org/results?team=9565), don't work because there is a Cloudflare captcha blocking the automation.


## Pre-requisites

Download [Firefox](https://www.firefox.com/en-US/thanks/) or any other Firefox fork


Download [Python](https://www.python.org/downloads/)


Download Selenium.
```
pip install selenium
```
