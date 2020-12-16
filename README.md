# fish-shop[BOT
 
# quiz_bot
 
Этот проект позволяет создать своего телеграм бота для магазина рыбы (Telegram). Этого бота еще нужно улучшать, стандарты MVP выполнены.
Бот работает на [CMS](https://www.elasticpath.com/)


## Подготовка к запуску Mac OS
Сначала зарегестрируйтесь на [redis](https://redis.io/)     
Уставновить [Python 3+](https://www.python.org/downloads/)

Установить, создать и активировать виртуальное окружение

```
pip3 install virtualenv
python3 -m venv env
source env/bin/activate
```

Установить библиотеки командой

```
pip3 install -r requirements.txt
```

Запуск бота   

```
python3 vk_bot.py
```

Создайте файл ".env" в него надо прописать ваши token'ы.   
В переменную `TG_TOKEN` его можно получить в отце всех ботов @botfather в телеграме.    
В переменную `MOTLIN_CLIENT_ID` его можно получить после регистрации на [сайте](https://www.elasticpath.com/request-free-trial).    
В переменную `REDIS_HOST` адрес базы данных.    
В переменную `REDIS_PORT` порт базы данных.    
В переменную `REDIS_PASSWORD` пароль от базы данных.    
    
**Пример**  
```
MOTLIN_CLIENT_ID=JfO9ujSynGVjh1Wd69sep7XJ75EIHvVad0jJtm40MM
VK_TOKEN=74a0755ce12b361b1a036811792f842e09c885d3ec4d33d5d903552268678488c250029645fa607c1ccdf
REDIS_HOST=redis-14895.c92.us-east-1-3.ec2.cloud.redislabs.com
REDIS_PORT=11835
REDIS_PASSWORD=s2aH9KMojd4afChrCtOxxKbdzwRO2hSR
```
