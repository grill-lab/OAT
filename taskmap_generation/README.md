# TaskMap Generation: where the magic happens ;)

## Local Development

Download datasets (from within InternalGRILL folder):
``` 
$ bash taskmap_generation/setup.sh --local
```

Setup environment using minikube (from within InternalGRILL folder):
``` 
$ cd InternalGRILL/
$ minikube start
$ minikube tunnel &
$ minikube dashboard &
$ minikube mount ./shared:/shared 
```

Setup environment using docker-compose (from within InternalGRILL folder):
``` 
$ docker compose up --build
```

Access jupyter notebook:
``` 
$ http://localhost:7777/lab
```

Access jupyter notebook:
``` 
$ cd ../taskmap_generation
$ python3 main.py
```

## AWS Development

TODO

