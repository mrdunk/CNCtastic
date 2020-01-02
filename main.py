import common
from coordinator.coordinator import Coordinator

def main():
    controllers = common.loadPlugins("controllers").values()
    interfaces = common.loadPlugins("interfaces").values()
    coordinator = Coordinator(interfaces, controllers)

    while True:
        coordinator.update()


if __name__ == "__main__":
    main()
