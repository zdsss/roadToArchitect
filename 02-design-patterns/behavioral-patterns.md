# 行为型模式（Behavioral Patterns）

行为型模式关注的是算法以及对象之间职责的分配。

---

## 1. 观察者模式（Observer）

### 意图
定义一种一对多的依赖关系，使得当一个对象的状态发生变化时，所有依赖它的对象都能被自动通知并更新。

### 适用场景
- 事件系统、发布/订阅机制、响应式 UI
- 当一个对象的变化需要触发其他对象变化，但不知道具体有多少对象需要改变时

### 伪代码
```python
class EventBus:
    def __init__(self):
        self._listeners = defaultdict(list)
    def subscribe(self, event, fn):
        self._listeners[event].append(fn)
    def publish(self, event, data):
        for fn in self._listeners[event]:
            fn(data)
```

### 真实案例
- DOM 事件监听器
- 消息中间件（Kafka、RabbitMQ 的主题机制）
- React 状态管理 / Redux

---

## 2. 策略模式（Strategy）

### 意图
定义一组算法，将每个算法封装起来，并使它们可以相互替换。

### 适用场景
- 同一算法存在多种变体
- 需要在运行时动态切换算法
- 避免使用大量条件分支来选择不同的算法变体

### 伪代码
```python
class Sorter:
    def __init__(self, strategy):
        self.strategy = strategy
    def sort(self, data):
        return self.strategy(data)

sorter = Sorter(strategy=merge_sort)
sorter.sort([3, 1, 2])
```

### 真实案例
- 支付处理器（Stripe、PayPal、银行转账——每种都是一个策略）
- 路由算法（最短路径、最少跳数）
- 压缩策略（gzip、brotli、lz4）

---

## 3. 命令模式（Command）

### 意图
将请求封装为一个对象，从而支持参数化、排队、日志记录以及可撤销的操作。

### 适用场景
- 撤销/重做功能
- 操作的排队或延迟调度
- 操作的审计日志
- 事务性行为

### 伪代码
```python
class Command:
    def execute(self): ...
    def undo(self): ...

class MoveFileCommand(Command):
    def execute(self): os.rename(src, dst)
    def undo(self): os.rename(dst, src)

history = []
cmd = MoveFileCommand(src, dst)
cmd.execute()
history.append(cmd)
# later: history.pop().undo()
```

### 真实案例
- 数据库事务日志
- UI 撤销栈（Photoshop、Google Docs）
- 任务队列（Celery 任务本质上就是命令）

---

## 4. 责任链模式（Chain of Responsibility）

### 意图
将请求沿着一条处理链传递，链上的每个处理器决定自己处理还是将请求传递给下一个。

### 适用场景
- 可能有多个对象处理同一请求
- 处理器在运行前无法预先确定
- 请求应由多个候选处理器中的某一个来处理

### 伪代码
```python
class Handler:
    def __init__(self, next_handler=None):
        self.next = next_handler
    def handle(self, request):
        if self.can_handle(request):
            return self.process(request)
        elif self.next:
            return self.next.handle(request)
```

### 真实案例
- HTTP 中间件（认证 → 限流 → 日志 → 处理器）
- 客服升级层级（L1 → L2 → L3）
- 异常处理链

---

## 5. 模板方法模式（Template Method）

### 意图
在基类中定义算法的骨架，将某些步骤的具体实现延迟到子类中。

### 适用场景
- 算法中不变的部分放在基类中
- 子类负责实现可变的部分
- 通过钩子方法控制子类的扩展行为

### 伪代码
```python
class DataProcessor:
    def process(self):   # template method
        data = self.read()
        data = self.transform(data)
        self.write(data)

    def read(self): raise NotImplementedError
    def transform(self, data): return data  # default hook
    def write(self, data): raise NotImplementedError
```

### 真实案例
- Django 基于类的视图（`get()`、`post()` 重写 `dispatch()`）
- JUnit 测试生命周期（`setUp`、`test`、`tearDown`）

---

## 6. 状态模式（State）

### 意图
允许对象在内部状态改变时改变其行为，使其看起来像是改变了自身的类。

### 适用场景
- 对象的行为严重依赖其所处状态
- 代码中大量基于状态的条件分支
- 有限状态机场景

### 伪代码
```python
class Order:
    def __init__(self):
        self.state = PendingState()
    def confirm(self):
        self.state = self.state.confirm(self)
    def ship(self):
        self.state = self.state.ship(self)
```

### 真实案例
- 订单生命周期（待确认 → 已确认 → 已发货 → 已签收）
- TCP 连接状态（LISTEN → SYN_SENT → ESTABLISHED → CLOSE_WAIT）
- 交通信号灯

---

## 7. 迭代器模式（Iterator）

### 意图
提供一种方式，可以顺序访问集合中的元素，而无需暴露其底层的数据结构。

### 真实案例
- 数据库游标
- Python 生成器（`yield`）
- Kafka 消费者遍历分区

---

## 架构师核心要点

1. **观察者模式/事件总线** 将生产者与消费者解耦——是事件驱动架构的基础。
2. **策略模式** 替代 `if/else` 嵌套——优先使用组合而非继承。
3. **命令模式** 支持撤销、排队和审计追踪——适用于 CQRS 的写端。
4. **责任链模式** 是所有中间件框架底层的工作机制。
5. **状态机** 的使用率被低估——它能让复杂的生命周期逻辑变得清晰且易于测试。
