# FAQ


## Can a dataclass be a dependency?

Yes, for sure

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


## Do postponed annotations work correctly?

Yes, they do

```python
@di.inject
def func(arg: Annotated["SomeClass", ...]):
    return arg

func()  # this works fine if SomeClass is present in the di container at the time of this call
```

## How dimi resolves string-based dependencies?
Each container instance keeps an auxiliary dictionary which maps callable names (`__name__` attribute) to the callables themselves.

!!! warning
    Storing two dependencies with the same `__name__` inside one DI container is not supported
