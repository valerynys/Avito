## Запуск

Для вашего удобства я захостил приложение на [Avito intern](http://82.148.28.123:8080), но если есть желание то можно
посмотреть на инструкцию ниже.

Создайте .env файл в корне проекта с переменными
```
SERVER_ADDRESS=
POSTGRES_CONN=
POSTGRES_JDBC_URL=
POSTGRES_USERNAME=
POSTGRES_PASSWORD=
POSTGRES_HOST=
POSTGRES_PORT=
POSTGRES_DATABASE=
```
Заполните в соответствии с credentials cnrprod1725724486-team-76925_pgsql.txt
[PostgreSQL credentials](https://git.codenrock.com/avito-testirovanie-na-backend-1270/cnrprod1725724486-team-76925/credentials/-/blob/main/cnrprod1725724486-team-76925_pgsql.txt?ref_type=heads)

Соберите и запустите контейнер
```
docker build -t fastapi-app .

docker run -d --name fastapi-container -p 8080:8080 --env-file .env fastapi-app
```

Экспортируйте .env файл командой ```export $(grep -v '^#' .env | xargs)```

Если база вдруг будет недоступна можно запустить локально изменив .env
```docker-compose up -d --build```

## Задание
В папке "задание" размещена задача.

## Сбор и развертывание приложения
Приложение должно отвечать по порту `8080` (жестко задано в настройках деплоя). После деплоя оно будет доступно по адресу: `https://<имя_проекта>-<уникальный_идентификатор_группы_группы>.avito2024.codenrock.com`

Пример: Для кода из репозитория `/avito2024/cnrprod-team-27437/task1` сформируется домен

```
task1-5447.avito2024.codenrock.com
```

**Для удобства домен указывается в логе сборки**

Логи сборки проекта находятся на вкладке **CI/CD** -> **Jobs**.

Ссылка на собранный проект находится на вкладке **Deployments** -> **Environment**. Вы можете сразу открыть URL по кнопке "Open".

## Доступ к сервисам

### Kubernetes
На вашу команду выделен kubernetes namespace. Для подключения к нему используйте утилиту `kubectl` и `*.kube.config` файл, который вам выдадут организаторы.

Состояние namespace, работающие pods и логи приложений можно посмотреть по адресу [https://dashboard.avito2024.codenrock.com/](https://dashboard.avito2024.codenrock.com/). Для открытия дашборда необходимо выбрать авторизацию через Kubeconfig и указать путь до выданного вам `*.kube.config` файла



