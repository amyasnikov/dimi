<div align="center">
    <h1>Tiny DI - Easy Dependency Injection for Python</h1>
    <p>
        <img src="https://github.com/amyasnikov/tinydi/actions/workflows/ci.yaml/badge.svg" alt="CI">
        <img src="https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/amyasnikov/43fbe231840b4945691de15d43eb003d/raw/cov_tinydi.json" alt="Coverage">
        <img src="https://img.shields.io/badge/Python-3.9|3.10|3.11|3.12-blue.svg" alt="Python version">
    </p>
</div>


> *“Dependency Injection” is a 25-dollar term for a 5-cent concept.*
>
> James Shore


Tired of complex abstractions? Tired of things like *"to do dependency injection let's first dive into providers, scopes and binders"*?


Just want to inject dependencies and mock them during tests?

Say no more!

## Installation

```
pip install tinydi
```

## Getting Started

```python
from tinydi import TinyDI
from typing import Annotated
from flask import Flask, jsonify

# DI container instance stores all the dependencies you place inside
di = TinyDI()


# dependency is a function, async function or a class
# it can be added to the container via the following decorator:

@di.dependency
def get_weather_service_url():
    return 'https://awesome-weather-provider.com/api'


# Dependency may have sub-dependencies defined via typing.Annotated
# For TinyDI mostly the second part of Annotated matters, the first part is for type checkers

@di.dependency
class WeatherService:
    def __init__(self, url: Annotated[str, get_weather_service_url])
        self.url = url

    def get_weather(self, city): ...


app = Flask(__name__)

# Annotated[MyCls, ...] is the shortcut for Annotated[MyCls, MyCls]

@app.route("/api/weather/<city>")
@di.inject
def get_weather(city: str, weather_service: Annotated[WeatherService, ...]):
    return jsonify(weather_service.get_weather())

```

The DI container also supports dict-like way of retrieving the dependencies:

```python
weather_service = di[WeatherService]
print(weather_service.get_weather('london'))
```


## OK, but where is the profit?

Someone may ask, "Why not just do this instead?"

```python
# the same API handle but w/o DI

@app.route("/api/weather/<city>")
def get_weather(city: str):
    return jsonify(
        WeatherService('https://awesome-weather-provider.com/api').get_weather(city)
    )
```

The simplest argument for DI is **easier testing**.

How would you test the non-DI API handle above? I guess something nasty with monkey patches.

But with DI in action everything becomes much simpler and more obvious:

```python
from myapp import di  # instance of the TinyDI container
from myapp.services import WeatherService


def test_weather_api_handle(test_client):
    class MockWeatherService:
        def weather(self, city):
            return {'temperature': 30.5, 'wind_speed': 3.1, 'city': city}

    # override() preserves and restores DI container state after exit from context manager
    with di.override():
        di[WeatherService] = MockWeatherService
        weather = test_client.get('/api/weather/london').json()
        assert weather == {'temperature': 30.5, 'wind_speed': 3.1, 'city': 'london'}

```

## Key Benefits

* Simple and concise API:
    * Ask for dependencies via `Annotated[SomeType, some_callable]` type annotation
    * Add callables to the DI container via `@di.dependency`
    * Do injections via `@di.inject`
    * override DI contents via `di.override()`
* Auto sub-dependencies resolving. **A** may depend on **B** which may depend on **C** which may depend on **D** and **E** and so on. All of this will be correctly tied together and resolved at the time of a function call
* Optional scopes. Just use `@di.dependency(scope=Singleton)` to cache first call of a function for the lifetime of the app.
* Short codebase of around 200 lines of code. Even if the author was hit by a bus, it would not be a big deal to fork the repository and make the required changes.
* Async support
* Thread safety

## Docs

Want to know more? Welcome to the [docs](https://tinydi.readthedocs.io)
