-- Создаёт таблицу urls, если она не существует
CREATE TABLE IF NOT EXISTS urls (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,  -- Уникальный идентификатор (автоинкремент)
    name VARCHAR(255) NOT NULL UNIQUE,  -- URL должен быть уникальным
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP  -- Дата создания записи
);

-- Создаёт таблицу url_checks, если она не существует
CREATE TABLE IF NOT EXISTS url_checks (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,  -- Уникальный идентификатор (автоинкремент)
    url_id BIGINT REFERENCES urls (id) ON DELETE CASCADE,  -- Внешний ключ, связанный с urls
    status_code INTEGER,  -- Код ответа HTTP
    h1 VARCHAR(255),  -- Заголовок h1
    title VARCHAR(255),  -- Заголовок title
    description TEXT,  -- Описание страницы
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP  -- Дата проверки
);
