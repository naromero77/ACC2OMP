# Change Log

Notable changes to ACC2OMP are documented in this file

## [0.2.2] - 2020-XX-YY

Minor enhancements:
- Support OpenACC present directive
- More robust handling of directives that translates into nothing

Bug fix:
- Arguements to directives were being forced into lowercase

## [0.2.1] - 2020-01-23

Minor enhancements:
- Original OpenACC directives can be maintained in output.
- Prettify formatting when commas are present.

## [0.2] - 2020-01-10

Production Release

Conversion tool hardened on at least one real science code.
Previously, lines with non-supported directives where completely
deleted from source-2-source translation. Instead we now detect
lines that are only partially translated and retain the original
OpenACC.

## [0.1] - 2019-08-01

Initial Release

# Notes for File Format

## [Release Number] - YYYY-MM-DD

Document major changes
