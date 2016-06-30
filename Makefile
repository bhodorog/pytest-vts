test:
	tox -- ./tests

pypi-sdist-clean:
	rm -rf ./dist

pypi-sdist: test pypi-sdist-clean
	python setup.py egg_info sdist

pypi-upload: pypi-sdist
	$(eval TAG := "v"$(shell python setup.py --version))
	.tox/default/bin/twine upload --username bhodorog dist/*tar.gz
	git -c 'user.name=Bogdan Hodorog' -c 'user.email=bogdan.hodorog@gmail.com' tag -a -m "Manually built using make" $(TAG)
	git push origin $(TAG)

.PHONY: test
.PHONY: pypi-sdist-clean pypi-sdist pypi-upload
