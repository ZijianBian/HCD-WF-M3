Contributing
============

Thank you for your interest in contributing to HCD Workflow!

Code of Conduct
---------------

* Be respectful and professional
* Focus on constructive feedback
* Help maintain code quality
* Document your changes

Getting Started
---------------

1. Fork/clone the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

Development Process
-------------------

Branching Strategy
~~~~~~~~~~~~~~~~~~

* ``main`` - Production releases
* ``develop`` - Development branch
* ``feature/*`` - New features
* ``bugfix/*`` - Bug fixes
* ``release/*`` - Release preparation

Creating a Feature Branch
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   git checkout develop
   git pull
   git checkout -b feature/my-feature-name

Making Changes
~~~~~~~~~~~~~~

1. Write clear, concise code
2. Follow existing code style
3. Add docstrings to functions/classes
4. Update relevant documentation

Code Style
----------

We follow PEP 8 with some modifications:

* Line length: 120 characters
* Use Black for formatting
* Use flake8 for linting
* Use pylint for code quality

Formatting Code
~~~~~~~~~~~~~~~

.. code-block:: bash

   # Format all code
   black --line-length 120 hcdworkflow/ gui/ tools/ workflow/
   
   # Check style
   flake8 --max-line-length=120 --ignore=E203,W503 hcdworkflow/
   
   # Run pylint
   pylint --max-line-length=120 hcdworkflow/

Testing
-------

Before Submitting
~~~~~~~~~~~~~~~~~

Test your changes with the test data:

.. code-block:: bash

   # Test single slice
   hcdslice_nogui -c tests/data/GRAYSCALE/
   
   # Test full workflow
   hcd_nogui -c tests/data/GRAYSCALE/
   
   # Test GUI (if applicable)
   hcd_gui

Run Static Analysis
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   bash ci-sdcc/st05-staticanalysis.sh

Commit Guidelines
-----------------

Commit Message Format
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   <type>: <subject>
   
   <body>
   
   <footer>

Types:

* ``feat``: New feature
* ``fix``: Bug fix
* ``docs``: Documentation changes
* ``style``: Code style changes (formatting)
* ``refactor``: Code refactoring
* ``test``: Adding/updating tests
* ``chore``: Maintenance tasks

Example:

.. code-block:: text

   feat: Add support for new ECRH actor
   
   - Integrate TORBEAM actor
   - Add configuration template
   - Update documentation
   
   Closes #123

Pull Request Process
--------------------

1. Update documentation for new features
2. Ensure all tests pass
3. Update CHANGELOG if applicable
4. Request review from maintainers
5. Address review comments

Pull Request Template
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: markdown

   ## Description
   Brief description of changes
   
   ## Type of Change
   - [ ] Bug fix
   - [ ] New feature
   - [ ] Documentation update
   - [ ] Code refactoring
   
   ## Testing
   - [ ] Tested with test data
   - [ ] Manual testing performed
   - [ ] Static analysis passed
   
   ## Checklist
   - [ ] Code follows style guidelines
   - [ ] Documentation updated
   - [ ] No breaking changes
   - [ ] Commits are properly formatted

Documentation
-------------

Updating Documentation
~~~~~~~~~~~~~~~~~~~~~~

Documentation is in ``docs/source/`` directory.

.. code-block:: bash

   # Edit .rst files
   vim docs/source/user/usage.rst
   
   # Build documentation
   cd docs
   make html
   
   # View in browser
   firefox build/html/index.html

Documentation Style
~~~~~~~~~~~~~~~~~~~

* Use reStructuredText format
* Include code examples
* Add cross-references
* Keep it concise and clear

Adding New Commands
-------------------

If adding a new command-line tool:

1. Create the script in project root
2. Update ``pyproject.toml``:

   .. code-block:: toml

      py-modules = ["...", "new_command"]

3. Add documentation
4. Add usage examples

Adding New Actors
-----------------

1. Create actor wrapper
2. Add to ``global_lists.yaml``
3. Create configuration template in ``actor_install/``
4. Document in ``docs/source/reference/actors.rst``
5. Add test data if possible

Adding New Features
-------------------

1. Discuss on issue tracker first
2. Design the feature
3. Implement with tests
4. Document thoroughly
5. Submit pull request

Bug Reports
-----------

When reporting bugs, include:

* HCD Workflow version
* Python version
* Module versions (IMAS, actors)
* Configuration files (if applicable)
* Error messages and traceback
* Steps to reproduce

Bug Report Template
~~~~~~~~~~~~~~~~~~~

.. code-block:: markdown

   ## Bug Description
   Clear description of the bug
   
   ## Environment
   - HCD Workflow version: 2.4.1
   - Python version: 3.11
   - IMAS version: 5.4.0
   - Modules loaded: GRAYSCALE/1.1.0
   
   ## Steps to Reproduce
   1. Load module
   2. Run command
   3. See error
   
   ## Expected Behavior
   What should happen
   
   ## Actual Behavior
   What actually happens
   
   ## Error Output
   ```
   Paste error message here
   ```

Feature Requests
----------------

Feature Request Template
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: markdown

   ## Feature Description
   Clear description of the feature
   
   ## Use Case
   Why is this feature needed?
   
   ## Proposed Solution
   How should it work?
   
   ## Alternatives Considered
   Other approaches you've thought about

Review Process
--------------

All submissions require review. We use pull requests for this purpose.

Reviewers Will Check
~~~~~~~~~~~~~~~~~~~~

* Code quality and style
* Test coverage
* Documentation completeness
* Breaking changes
* Performance implications

Communication
-------------

* Issues: For bugs and feature requests
* Pull Requests: For code contributions
* Email: For private concerns
* Confluence: For design discussions

License
-------

By contributing, you agree that your contributions will be licensed under the same license as the project.

Recognition
-----------

Contributors will be acknowledged in:

* Release notes
* Contributors file
* Documentation (where appropriate)

Thank You!
----------

Thank you for contributing to HCD Workflow and helping improve plasma simulation tools for ITER!
