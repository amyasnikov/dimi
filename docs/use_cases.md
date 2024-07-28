## Usage with Django

```python
from config.dependencies import di  # application-wide instance of the container
from myapp.services import SomeService


# function-based view

@di.inject
def my_function_view(request, service: Annotated[SomeService, ...]):
    useful_info = service.get_some_info()
    return render(request, 'myapp/my_template.html', {'info': useful_info})


# class-based view

class MyClassView(View):
    @di.inject
    def __init__(self, service: Annotated: [SomeService, ...]):
        self.service = service
    ...
```

## Usage with Flask

```python
from myapp.dependencies import di  # application-wide instance of the container
from myapp.services import SomeService

@app.route("/api/service_info")
@di.inject
def service_info(service: Annotated[SomeService, ...]):
    return jsonify(service.get_some_info())

```

## Usage with FastAPI

FastAPI requires using its own `Depends` inside view function arguments. To comply with this requirement `Container.fastapi()` method is introduced.

```python
from fastapi import FastAPI

from myapp.dependencies import di  # application-wide instance of the container
from myapp.services import SomeService

app = FastAPI()


# di.inject decorator is not used
@app.get("/api/service_info")
async def service_info(service: Annotated[SomeService, di.fastapi(SomeService)]):
    return service.get_some_info()
```

Under the hood `di.fastapi(SomeService)` resolves the dependency as usual (using `di` container contents) and wraps it with `fastapi.Depends`.


## Dataclasses as dependencies

Dataclasses can be easily used as dependencies.

```python

@di.dependency
def get_url():
    return 'http://example.com'


@di.dependency
@dataclass
class A:
    url: Annotated[str, get_url]


assert di[A].url == 'http://example.com'
```
