# antispam-bot for telegram group
![TAB](https://github.com/nolka/telegram-antispam-bot/blob/readme-rewrite/logo.png?raw=true)
## Description
Simple telegram antispam bot written in python. Can be used in multiple groups simultaneously.
### Main functions:
* Checking the subscribers of your Telegram channel for activity in order to prevent the ingress of unwanted advertising information.
### Supported language:
* ru
## Technology stack:
* Python 3.11
* telebot 0.0.5
* Docker
## Preparing the bot for local work:
* Clone the repository: `$ git clone git@github.com:nolka/telegram-antispam-bot.git`
* Change directory to  telegram-antispam-bot: `$ cd telegram-antispam-bot`
* Create a virtual environment: `$ python -m venv venv`
* Activate the environment:
  * for Windows: `venv\Scripts\activate.bat`
  * for Mac/Linux:  `$ source ./venv/bin/activate`
* Update pip: `$ python pip install --upgrade pip`
* Install requirements: `$ pip install -r requirements.txt`
* Copy .env.example to .env
* Create telegram bot token using @BotFather bot in telegram and append it in .env with bot user name
* Run bot: `$ python3 ./main.py`

## Running bot in docker
* Clone the repository: `$ git clone git@github.com:nolka/telegram-antispam-bot.git`
* Change directory to  telegram-antispam-bot: `$ cd telegram-antispam-bot`
* Copy .env.example to .env
* Create telegram bot token using @BotFather bot in telegram and append it in .env with bot user name
* Run bot: `$ python3 ./main.py`
* Run docker: `$ docker compose up`