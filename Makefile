test:
	tox

pypi-sdist-clean:
	rm -rf ./dist

pypi-sdist-wheel: test pypi-sdist-clean
	python setup.py egg_info sdist
	tox -e wheel

pypi-upload: pypi-sdist-wheel
	$(eval TAG := "v"$(shell python setup.py --version))
	tox -e twine -- upload --username bhodorog dist/*
	git -c 'user.name=Bogdan Hodorog' -c 'user.email=bogdan.hodorog@gmail.com' tag -a -m "Manually built using make" $(TAG)
	git push origin $(TAG)

.PHONY: test
.PHONY: pypi-sdist-clean pypi-sdist pypi-upload
