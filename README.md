# ViKtor Discord Music Bot

**Пригласить бота к себе можно по [ссылке](https://discord.com/api/oauth2/authorize?client_id=821326877213327371&permissions=8&scope=bot%20applications.commands)**


## Запуск у себя

Для любого метода:

Выставите **Privileged Gateway Intents** в [настройках бота](https://discord.com/developers/applications/)

**Скопируйте ссылку на бота** со скопами *bot* и *application.commands*

Также рекомендуется выдать ему права администратора


### Запуск через Docker Compose

Не забудьте закинуть токены в `.env` используя `nano .env`

```back
cp .env.example .env
nano .env
docker-compose up --build -d
```

Посмотреть логи
```bash
docker-compose logs -f
```

Убить ботика
```bash
docker-compose down
```

## Запуск ручками (вдруг захочется)

Установите Python3.10 [*(ссылка)*](https://www.python.org/downloads/)
```bash
git clone https://github.com/dogekiller21/ViKtor_Music_Bot
```

Создайте виртуальное окружение
```bash
python -m venv venv
```

Активируйте виртуальное окружение

Win:
```cmd
venv/Scripts/activate.bat
```

Linux:
```bash
source venv/bin/activate
```

Установите необходимые пакеты в свое окружение с помощью
```bash
pip install -r requirements.txt
pip install vkwave
pip install --upgrade typing_extensions==4.5.0
```

Установите ffmpeg

Win: [*(Инструкция)*](https://phoenixnap.com/kb/ffmpeg-windows)

Linux:
```bash
sudo apt install ffmpeg
```

Установите и запустите **postgresql** [_**(Инструкция)**_](https://www.postgresql.org/download/)

Создайте новую **БД** (стандартное название - app) [_**(Инструкция)**_](https://postgrespro.ru/docs/postgresql/9.5/manage-ag-createdb)

Переименуйте файл `.env.example` в `.env` и **заполните его токенами и данными для подключения к БД** *(про токены смотрите ниже)*

Запустите `main.py` в корневой папке
```bash
python main.py
```

### Решение проблем с зависимостью
* Установите все пакеты из requirements.txt (`pip install -r requirements.txt`)
* Установите `vkwave` (`pip install vkwave`)
* Установите `typing_extensions==4.5.0` (`pip install --upgrade typing_extensions==4.5.0`)

### Необходимые токены

#### DC_TOKEN
Токен Discord Бота получается в [настройках бота](https://discord.com/developers/applications/)
#### VK_TOKEN
VK токен - можно получить [тут](https://vkhost.github.io/) (в данный момент нормально работает токен от Маруси)
#### GENIUS_TOKEN
Токен Genius Lyrics - получать [тут](https://genius.com/api-clients) *(CLIENT ACCESS TOKEN)*