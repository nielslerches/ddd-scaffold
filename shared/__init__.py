from punq import Container

__all__ = ('set_container', 'get_container')
_container = None


def set_container(container: Container):
    global _container
    _container = container


def get_container() -> Container:
    global _container
    return _container
