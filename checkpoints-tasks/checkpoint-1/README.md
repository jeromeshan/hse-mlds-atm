# Чекпоинт 1

### Первый этап 
Основной задачей на первом этапе будет обагощение данных за счет внешних открытых источников (OSM, Яндекс Карты)

Идеи для обогащения датасета:
* Классика: расстояния до объектов инфраструктуры (кафе, театры, метро и тп)
* Попытаться посчитать трафик, если не получится достать, то придумать прокси к трафику
* Попытаться сделать метрику качества трафика 
* Попытаться сделать реверс инжениринг нашего таргета

Вопросы: 
* Что значит таргет в трейне? На основе чего эта метрика оптимальности расчитана
* Будем пытаться охватить всю Россию или остановимся на одном регионе?

### Второй этап 
Решаем задачу в лоб: делаем как можно более качественную модель предсказывающую таргет
Возможные модели: деревья/леса, регрессии, бустинг

### Третий этап 
Переформулировать задачу из этапа 2, в задачу решаемую моделями нейронных сетей

### Червертый этап
Реализовать сервис (скорее всего вэб-сервис) для автоматического расчета/визуализации популярности банкоматов