test:
	tox -- ./tests

pypi-sdist-clean:
	rm -rf ./dist

pypi-sdist: test pypi-sdist-clean
	python setup.py egg_info sdist

pypi-upload: pypi-sdist
	git tag -a -m "Built by make on circleCI" "v"$(shell python setup.py --version)
	.tox/default/bin/twine upload --username bhodorog dist/*tar.gz
	git push origin --tags

.PHONY: test
.PHONY: pypi-sdist-clean pypi-sdist pypi-upload
