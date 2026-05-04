import reprlib
# import array
# from collections import deque

class SmartRepr(reprlib.Repr):
    # ==================== 1. 基础序列：list / tuple
    def repr_list(self, x, level):
        return self._repr_safe_seq(x, level, '[', ']', self.maxlist)

    def repr_tuple(self, x, level):
        return self._repr_safe_seq(x, level, '(', ')', self.maxtuple)

    # ==================== 2. 集合：set / frozenset
    def repr_set(self, x, level):
        return self._repr_safe_seq(x, level, '{', '}', self.maxset)

    def repr_frozenset(self, x, level):
        return self._repr_safe_seq(x, level, 'frozenset({', '})', self.maxfrozenset)

    # ==================== 3. 队列：deque
    # def repr_deque(self, x, level):
    #     return self._repr_safe_seq(x, level, 'deque([', '])', self.maxdeque)

    # ==================== 4. 数组：array.array
    def repr_array(self, x, level):
        return self._repr_safe_seq(x, level, f"array({x.typecode!r}, [", '])', self.maxarray)

    # ==================== 5. 字典：dict
    def repr_dict(self, x, level):
        maxl = self.maxdict
        n = len(x)
        if n <= maxl:
            return super().repr_dict(x, level)
        half = maxl // 2
        newlevel = level - 1
        repr1 = self.repr1
        items = list(x.items())
        head = items[:half]
        tail = items[-half:]
        head_pieces = [f"{repr1(k, newlevel)}: {repr1(v, newlevel)}" for k, v in head]
        tail_pieces = [f"{repr1(k, newlevel)}: {repr1(v, newlevel)}" for k, v in tail]
        return '{' + ', '.join(head_pieces + ['...'] + tail_pieces) + '}'

    # ==================== 6. 字符串：str
    def repr_str(self, x, level):
        maxl = self.maxstring
        if len(x) <= maxl:
            return super().repr_str(x, level)
        half = maxl // 2
        return repr(x[:half] + '...' + x[-half:])

    # ==================== 7. 整数（修复版）
    # def repr_int(self, x, level):
    #     s = str(x)
    #     maxl = self.maxlong
    #     if len(s) <= maxl:
    #         return repr(x)
    #     half = maxl // 2
    #     # 直接返回字符串格式，不尝试转int！
    #     return repr(s[:half] + '...' + s[-half:])

    # # ==================== 8. 兜底：其他对象
    # def repr_other(self, x, level):
    #     res = super().repr_other(x, level)
    #     maxl = self.maxother
    #     if len(res) <= maxl:
    #         return res
    #     half = maxl // 2
    #     return res[:half] + '...' + res[-half:]

    # ==================== 万能安全序列：所有类型都兼容，先转list再切片
    def _repr_safe_seq(self, x, level, left, right, maxl):
        n = len(x)
        lst = list(x)  # 统一转列表，100%兼容所有可迭代对象
        if n <= maxl:
            return left + ', '.join(self.repr1(i, level-1) for i in lst) + right
        half = maxl // 2
        head = [self.repr1(i, level-1) for i in lst[:half]]
        tail = [self.repr1(i, level-1) for i in lst[-half:]]
        return left + ', '.join(head + ['...'] + tail) + right