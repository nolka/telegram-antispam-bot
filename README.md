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
## Preparing the bot for work:
* Clone the repository: ```git clone <SSH key>```
* Create a virtual environment: ```python -m venv venv```
* Activate the environment:
  * for Windows: ```source venv/Scripts/activate```
  * for Mac/Linux:  ```source venv/bin/activate```
* Update pip: ```python pip install --upgrade pip```
* Install requirements: ```pip install -r requirements.txt```
* The .env.example file contains the code of the .env file required for the anti-spam bot to work.
