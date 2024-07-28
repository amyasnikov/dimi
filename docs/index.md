# Welcome to dimi Documentation

**dimi** is a minimalistic library for Dependency Injection in Python

## What is Dependency Injection

Dependency Injection is a very basic programming principle which simply says:

*Instead of creating an instance of something by yourself, get it as a parameter.*

Simple example:

```python
# without DI

class WeatherService:
    def get_air_temperature(self, city):
        provider = AwesomeWeatherProvider(api_key=os.getenv("AWESOME_API_KEY"))
        return provider.get_weather(city).temperature
```

In the example above the `WeatherService` is very highly coupled with

* `AwesomeWeatherProvider`
* `AWESOME_API_KEY` environment variable

This can cause problems with:

* **Unit tests.** To unit-test the code above we have to do monkey-patching to replace the real provider with the mock one. The main problem here is fragility. Monkey-patching changes what is not supposed to be changed, the implementation details. All of this can be easily broken if implementation changes some way.
* **Code maintainability.** What if we want to change the provider? What if we want to change the method how the API key is stored? In both of these cases the code above has to be rewritten.

Let's rewrite the code above according to Dependency Injection principle:

```python
# With DI

class WeatherService:
    def __init__(self, weather_provider):
        self.weather_provider = weather_provider

    def get_air_temperature(self, city):
        return self.weather_provider.get_weather(city).temperature


def main():
    # assembling the dependencies
    weather_service = WeatherService(
        provider=AwesomeWeatherProvider(
            api_key=os.getenv("AWESOME_API_KEY")
        )
    )
```

## The Role of Dependency Injection Libraries

As you can see above, you don't have to have any libraries to implement DI in your code.

The libraries (including **dimi**) can help you in two ways:

* Reduce and structure the code required to assemble the dependencies
* Inject dependencies into the entities which are not directly called by you, e.g. Django views.


## Installation and Getting Started

To install the library issue

```
pip install dimi
```

After that follow the guide listed in [README.md](https://github.com/amyasnikov/dimi?tab=readme-ov-file#getting-started) or check out [dimi API](di_api.md)
