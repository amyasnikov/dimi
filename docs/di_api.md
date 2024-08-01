# dimi API

First, you have to instantiate the container.

```python
from dimi import Container

di = Container()
```

All the dependencies are stored/assembled/injected from/to particular Container instance. If you have multiple container instances, they are completely independent.


## Adding dependencies to the Container

The container accepts **callable** objects to be placed inside

```python
@di.dependency # decorator puts the dependency inside the container
def get_service_config():
    return {'url': 'http://example.com', 'token': '1234'}

```
Alternatively, you can call it directly

```python
# put the dependency inside the container
di.dependency(get_service_config)
```

In fact, under the hood this decorator calls `di.__setitem__`, which may be used as well:

```python
di[get_service_config] = get_service_config
```

All the same syntax works as well for

* classes
* async functions

```python
@di.dependency
class A:
    def __init__(self):
        self.arg = 100

@di.dependency
async def async_func():
    return 'something_useful'
```


## Extracting dependencies from the container

"Extracting the dependency" means

* resolving sub-dependencies if they exist
* calling the callable being stored inside the container and providing the result.

There are two ways to extract a dependency:

* **dict-like API**

```python
# function result is provided
assert di[get_service_config] == {'url': 'http://example.com', 'token': 'abcdef123'}

# class instance is provided
assert di[A].arg == 100

# coroutine is provided and has to be awaited to retrieve the result
assert await di[async_func] == 'something_useful'
```

* **inject decorator**

Dependencies from the container may be injected as keyword arguments into functions/methods calls.

[typing.Annotated](https://docs.python.org/3/library/typing.html#typing.Annotated) is used to mark the requirement for a particular dependency

```python
from typing import Annotated

class ApiClient:
    @di.inject
    def __init__(self, config: Annotated[dict, get_service_config]):
        self.url, self.token = config['url'], config['token']

# Now ApiClient may be instantiated (called) without "config" argument,
# its value will be injected from the DI container

client = ApiCLient()
assert client.url == 'http://example.com'
```

The same works for functions (both sync and async):

```python
@di.inject
async def async_func2(arg: Annotated[str, async_func]):
    return "really_" + arg

assert await async_func2() == 'really_something_useful'
```

## Sub-dependencies and Annotated

* `Annotated[SomeType, some_callable]` can also be used to define a relationship between dependencies.

```python
@di.dependency
def get_f():
    return 'F'

@di.dependency
def get_g():
    return 'G'

@di.dependency
def get_fg(arg1: Annotated[str, get_f], arg2: Annotated[str, get_g])
    return arg1 + arg2


assert di[get_fg] == 'FG'
```

# Annotated syntax

As you may see from the examples above, `typing.Annotated` can be used for

* Wiring the dependencies between each other inside the DI Container
* Declaring dependencies for a function/method where these dependencies are going to be injected

For most of the cases **dimi** uses only second argument of the Annotated, while the first one is for the type checkers like mypy.

For the sake of convenience `Annotated[]` has multiple supported syntax options:

* `Annotated[int, my_function]` - base syntax for function-based dependency. Causes `my_function()` to be called and the result to be injected as the parameter value
* `Annotated[MyClass, MyClass]` and its shortcut `Annotated[MyClass, ...]` - causes `MyClass()` to be instantiated by calling its `__init__()` method.
* `Annotated[int, "my_function"]` - string-based annotation. It may be convenient option if you don't want to import `my_function` directly.
* `Annotated[int, "MyClass.some_param"]` - string-based annotation with parameter(s). May be very useful if you have a dedicated class which stores all the configuration of the app, but you want to inject only particular setting/parameter.


## Scopes

Scope may help you to cache first result of a function call and reuse it for the next calls.

The ways to define a Scope for a dependency:

* **decorator**
```python
from dimi import Singleton

@di.dependency(scope=Singleton)
async def async_func():
    print('This message will be printed only once due to caching')
    return 'something_useful'
```

* **dependency() call**

```python
di.dependency(async_func, scope=Singleton)
```

* **dict-like API**

```python
di[async_func] = Singleton(async_func)
```

#### Existing scopes

* `dimi.scopes.Singleton` caches the first call of a function and after that always returns the same cached value for the whole lifetime of the app.
* `dimi.scopes.Context` also caches the result of the first function call, but stores the value inside [contextvars.ContextVar](https://docs.python.org/3/library/contextvars.html) instance. Effectively it means that:
    * In async web frameworks like FastAPI each request has its own value inside `Context` scope, but within this request this value will be preserved.
    * Each thread also has its own separate value which will be preserved inside that thread


## Overriding

To temporarily override dependencies inside the container you can use `override()` context manager. It preserves the state of the DI container and restores it after exit.

```python
@di.dependency
def get_f():
    return 'F'

@di.dependency
def get_g():
    return 'G'

@di.dependency
def get_fg(arg1: Annotated[str, get_f], arg2: Annotated[str, get_g])
    return arg1 + arg2


assert di[get_fg] == 'FG'

with di.override():
    di[get_f] = lambda: 'q'
    assert di[get_fg] == 'qG'

assert di[get_fg] == 'FG'
```

`di.override()` also accepts optional `overridings: dict[Callable, Callable] | None` parameter:

```python
with di.override({get_f: lambda: 'q'}):
    assert di[get_fg] == 'qG'
```
