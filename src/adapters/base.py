import os

class LanguageAdapter:
    language = 'unknown'
    extensions = []

    def extract(self, filepath):
        raise NotImplementedError

    def extract_source(self, source, filepath='<unknown>'):
        raise NotImplementedError

    def _make_index(self, symbols, calls, imports, filepath):
        return {
            'file': os.path.abspath(filepath),
            'symbols': symbols,
            'calls': calls,
            'imports': imports,
        }
