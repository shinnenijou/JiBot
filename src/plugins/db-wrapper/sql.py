
class SQL:
    def __init__(self):
        self.__sections = []

    def __str__(self) -> str:
        return ' '.join(_ for _ in self.__sections) + ';'

    def add(self, string: str, end: str | None = None):
        self.__sections.append(string)

        if end is not None:
            self.__sections.append(end)

        return self

    def Select(self, attr: str):
        return self.add('SELECT').add(attr)
    
    def Where(self, condition: str):
        return self.add('WHERE').add(condition)
    
    def And(self, condition: str):
        return self.add('AND').add(condition)
    
    def From(self, table: str):
        return self.add('FROM').add(table)
    
    def InsertTo(self, table: str):
        return self.add('INSERT TO').add(table)
    
    def Create(self, table: str):
        return self.add('CREATE TABLE').add(table)
    
    def Drop(self, table):
        return self.add('DROP TABLE').add(table)
        
    def Values(self):
        return self.add('VALUES')

    def EndValues(self, count):
        if count < 0:
            return
        
        size = len(self.__sections)

        if size > 0 and self.__sections[-1] == ',':
            self.__sections.pop()

        if count > size:
            count = size
        
        self.__sections.insert(size - count, '(')
        return self.add(')')

    def Update(self, table: str):
        return self.add('UPDATE').add(table)

    def Set(self):
        return self.add('SET')
    
    def Delete(self, table: str):
        return self.add('DELETE FROM').add(table)