class SqlBuffer:
    def __init__(self, sql, conj='WHERE', alias=''):
        self._sql = sql
        self._conj = conj

        if alias and not alias.endswith('.'): alias += '.'
        self._alias = alias



    def alias(self, alias):
        if alias and not alias.endswith('.'): alias += '.'
        self._alias = alias

        return self


    def append_sql(self, appended):
        self._sql += f'\n\t{appended}'


    def append_where(self, appended):
        self._sql += f'\n\t{self._conj:>6} {appended}'
        if self._conj == "WHERE": self._conj = "AND"


    def add_date(self, column, date_start, date_end, ignore_time=False):
        if len(date_start) == 7: date_start += "-01"
        if len(date_end) == 7: date_end += "-01"

        time_start = "" if ignore_time else "00:00:00"
        time_end = "" if ignore_time else "23:59:59"
        
        self.append_where(f"{self._alias}{column} BETWEEN TO_TIMESTAMP('{date_start} {time_start}', 'yyyy-MM-dd HH:mm:ss', 'GMT+8') AND TO_TIMESTAMP('{date_end} {time_end}', 'yyyy-MM-dd HH:mm:ss', 'GMT+8')")

        return self


    def add(self, column, value):
        if value != "*": self.append_where(f"{self._alias}{column} = '{value}'")

        return self


    def add_in(self, column, values):
        if values and len(values) > 0 and '*' not in values:
            quoted = ','.join(f"'{v}'" for v in values)
            self.append_where(f"{self._alias}{column} IN ({quoted})")
        
        return self


    def add_in_sub(self, column, sql):
        sql = sql.replace("\n", "\n\t\t")
        self.append_where(f"{self._alias}{column} IN ({sql}\n\t\t   )")

        return self


    def add_like(self, column, value, add_percent=True):
        percent_sign = '%' if add_percent else ''
        self.append_where(f"{self._alias}{column} LIKE '{value}{percent_sign}'")
        
        return self


    def add_not_null(self, column):
        self.append_where(f"{self._alias}{column} IS NOT NULL")

        return self


    def add_between_str(self, column, start, end):
        self.append_where(f"{self._alias}{column} BETWEEN '{start}' AND '{end}'")

        return self


    def order_by(self, column):
        self.append_sql(f" ORDER BY {self._alias}{column}")

        return self





    @property
    def sql(self):
        return self._sql