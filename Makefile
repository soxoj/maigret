LINT_FILES=maigret wizard.py tests

test:
	coverage run --source=./maigret -m pytest tests
	coverage report -m
	coverage html

rerun-tests:
	pytest --lf -vv

lint:
	@echo 'syntax errors or undefined names'
	flake8 --count --select=E9,F63,F7,F82 --show-source --statistics ${LINT_FILES}

	@echo 'warning'
	flake8 --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics --ignore=E731,W503,E501 ${LINT_FILES}

	@echo 'mypy'
	mypy ${LINT_FILES}

speed:
	time python3 ./maigret.py --version
	python3 -c "import timeit; t = timeit.Timer('import maigret'); print(t.timeit(number = 1000000))"
	python3 -X importtime -c "import maigret" 2> maigret-import.log
	python3 -m tuna maigret-import.log

format:
	@echo 'black'
	black --skip-string-normalization ${LINT_FILES}

pull:
	git stash
	git checkout main
	git pull origin main
	git stash pop

clean:
	rm -rf reports htmcov dist

install:
	pip3 install .
