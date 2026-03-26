# 创建型模式（Creational Patterns）

创建型模式处理对象的创建机制，旨在以适合特定场景的方式创建对象。它们对实例化过程进行抽象，使系统独立于其对象的创建、组合和表示方式。

---

## 1. 单例模式（Singleton）

### 意图
确保一个类只有一个实例，并提供一个全局访问点。

### 适用场景
- 系统中需要恰好一个对象来协调各项操作（例如，配置管理器、日志记录器或线程池）
- 必须控制对共享资源的访问（数据库连接、文件系统）
- 希望避免反复创建开销较大的对象

### 结构
```
Singleton
├── -instance: Singleton  (static, private)
├── -Singleton()           (private constructor)
└── +getInstance(): Singleton  (static, public)
```

### 伪代码
```python
class Singleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.config = {}

# Usage
a = Singleton()
b = Singleton()
assert a is b  # True — same instance
```

### 实际应用场景
- **应用日志记录器**：单一的日志实例将所有日志消息路由到同一个输出流/文件，避免重复日志或文件句柄冲突。
- **数据库连接池**：一个连接池对象统一管理所有数据库连接，避免耗尽数据库连接数。

### 注意事项
- 使单元测试变得困难（全局状态）
- 可能是伪装的全局变量——应谨慎使用
- 在多线程环境中，getInstance() 必须进行同步处理

---

## 2. 工厂方法模式（Factory Method）

### 意图
定义一个用于创建对象的接口，但让子类决定实例化哪个类。工厂方法让一个类将实例化推迟到子类。

### 适用场景
- 一个类无法预知它所需要创建的对象类型
- 子类应该控制所创建的对象
- 希望封装对象创建逻辑，并对客户端隐藏具体类型

### 结构
```
Creator (abstract)
├── +factoryMethod(): Product   (abstract)
└── +operation()               (uses factoryMethod)

ConcreteCreator extends Creator
└── +factoryMethod(): ConcreteProduct

Product (interface)
ConcreteProduct implements Product
```

### 伪代码
```python
class Notification:  # Product interface
    def send(self, message): pass

class EmailNotification(Notification):
    def send(self, message):
        print(f"Email: {message}")

class SMSNotification(Notification):
    def send(self, message):
        print(f"SMS: {message}")

class NotificationFactory:  # Creator
    def create_notification(self, channel) -> Notification:
        if channel == "email":
            return EmailNotification()
        elif channel == "sms":
            return SMSNotification()
        raise ValueError(f"Unknown channel: {channel}")

# Usage
factory = NotificationFactory()
notif = factory.create_notification("email")
notif.send("Hello!")  # Email: Hello!
```

### 实际应用场景
- **UI 框架按钮**：跨平台 UI 库使用工厂方法，使 Windows 创建 `WindowsButton`、macOS 创建 `MacButton`，而客户端代码只调用 `createButton()`，无需知道具体类型。
- **支付处理器**：电商系统根据用户选择创建 `StripePayment`、`PayPalPayment` 或 `CryptoPayment` 对象。

---

## 3. 抽象工厂模式（Abstract Factory）

### 意图
提供一个接口，用于创建一**族**相关或相互依赖的对象，而无需指定其具体类。

### 适用场景
- 系统必须独立于其产品的创建方式
- 需要确保一族产品能够协同工作（UI 主题、特定操作系统的控件）
- 希望在产品族之间强制约束

### 结构
```
AbstractFactory (interface)
├── +createProductA(): AbstractProductA
└── +createProductB(): AbstractProductB

ConcreteFactory1 implements AbstractFactory
ConcreteFactory2 implements AbstractFactory

AbstractProductA / AbstractProductB (interfaces)
ConcreteProductA1, ConcreteProductA2 (implementations)
ConcreteProductB1, ConcreteProductB2 (implementations)
```

### 伪代码
```python
class GUIFactory:  # Abstract Factory
    def create_button(self): pass
    def create_checkbox(self): pass

class WindowsFactory(GUIFactory):
    def create_button(self):
        return WindowsButton()
    def create_checkbox(self):
        return WindowsCheckbox()

class MacFactory(GUIFactory):
    def create_button(self):
        return MacButton()
    def create_checkbox(self):
        return MacCheckbox()

def build_ui(factory: GUIFactory):
    button = factory.create_button()
    checkbox = factory.create_checkbox()
    button.render()
    checkbox.render()

# Usage
os_type = detect_os()
factory = WindowsFactory() if os_type == "windows" else MacFactory()
build_ui(factory)
```

### 实际应用场景
- **跨平台 UI 工具包**：Qt、wxWidgets 或 JavaFX 通过抽象工厂为每个操作系统生成原生外观的组件。
- **云服务商 SDK**：抽象工厂根据所配置的云服务商生成 `S3Bucket`/`AzureBlob`/`GCSBucket`，使应用程序代码与服务商无关。

### 工厂方法 vs. 抽象工厂

| | 工厂方法（Factory Method） | 抽象工厂（Abstract Factory） |
|---|---|---|
| 范围 | 单一产品 | 一族产品 |
| 机制 | 继承（子类重写） | 组合（注入工厂对象） |
| 适用场景 | 只有一种变化的产品类型 | 多种相关的产品类型 |

---

## 4. 建造者模式（Builder）

### 意图
将一个复杂对象的构建与其表示分离，使得同一个构建过程可以创建不同的表示。

### 适用场景
- 对象需要大量可选参数（避免重叠构造函数）
- 构建过程涉及必须按特定顺序执行的多个步骤
- 希望从相同数据生成不同表示（例如，XML 报告与 JSON 报告）

### 结构
```
Director
└── +construct(builder: Builder)

Builder (interface)
├── +buildPartA()
├── +buildPartB()
└── +getResult(): Product

ConcreteBuilder implements Builder
Product
```

### 伪代码
```python
class QueryBuilder:
    def __init__(self):
        self._table = ""
        self._conditions = []
        self._columns = ["*"]
        self._limit = None

    def from_table(self, table):
        self._table = table
        return self  # fluent interface

    def select(self, *columns):
        self._columns = list(columns)
        return self

    def where(self, condition):
        self._conditions.append(condition)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def build(self):
        cols = ", ".join(self._columns)
        sql = f"SELECT {cols} FROM {self._table}"
        if self._conditions:
            sql += " WHERE " + " AND ".join(self._conditions)
        if self._limit:
            sql += f" LIMIT {self._limit}"
        return sql

# Usage
query = (
    QueryBuilder()
    .from_table("users")
    .select("id", "name", "email")
    .where("active = 1")
    .where("age > 18")
    .limit(100)
    .build()
)
# SELECT id, name, email FROM users WHERE active = 1 AND age > 18 LIMIT 100
```

### 实际应用场景
- **HTTP 请求构建器**：Python 的 `requests` 或 Java 的 `HttpClient.newBuilder()` 等库使用建造者模式构建带有可选请求头、超时、请求体等的请求。
- **文档生成器**：通过替换不同的具体建造者，从相同数据生成 PDF、HTML 或 Markdown 报告。
- **测试数据工厂**：在测试中创建复杂领域对象，无需传入数十个构造函数参数。

---

## 5. 原型模式（Prototype）

### 意图
使用原型实例指定要创建的对象种类，并通过**复制**（克隆）该原型来创建新对象。

### 适用场景
- 对象创建开销较大（复杂初始化、数据库查询），而复制的代价更低
- 运行时需要带有细微差异的对象副本
- 要实例化的类在运行时才确定（例如，动态插件加载）
- 希望避免构建工厂类的继承层次

### 结构
```
Prototype (interface)
└── +clone(): Prototype

ConcretePrototype implements Prototype
└── +clone(): Prototype  (returns copy of self)

Client
└── uses prototype.clone() instead of new ConcretePrototype()
```

### 伪代码
```python
import copy

class DocumentTemplate:
    def __init__(self, title, sections, styles):
        self.title = title
        self.sections = sections   # list — mutable
        self.styles = styles       # dict — mutable

    def clone(self):
        # Deep copy ensures nested objects are independent
        return copy.deepcopy(self)

# Create a prototype
base_report = DocumentTemplate(
    title="Monthly Report",
    sections=["Summary", "Details", "Appendix"],
    styles={"font": "Arial", "size": 12}
)

# Clone and customize — base_report is untouched
march_report = base_report.clone()
march_report.title = "March 2026 Report"
march_report.sections.append("Q1 Forecast")
```

### 浅拷贝（Shallow Copy）与深拷贝（Deep Copy）

| | 浅拷贝（Shallow Copy） | 深拷贝（Deep Copy） |
|---|---|---|
| 基本类型 | 按值复制 | 按值复制 |
| 嵌套对象 | 共享引用 | 独立的新副本 |
| 适用场景 | 无嵌套可变状态 | 存在嵌套可变对象 |

### 实际应用场景
- **游戏敌人**：游戏通过克隆预配置的原型来生成数十个敌人实例，而无需重新加载资源和执行初始化逻辑。
- **配置模板**：部署系统将基准服务器配置作为原型保存，每个环境克隆后仅覆盖差异值。
- **细胞分裂比喻**：生物学灵感——模板分裂产生配置好的后代。

---

## 汇总表

| 模式 | 解决的问题 | 核心机制 |
|---|---|---|
| 单例（Singleton） | 只允许一个实例 | 私有构造函数 + 静态访问器 |
| 工厂方法（Factory Method） | 将创建与使用解耦（单一类型） | 子类重写创建方法 |
| 抽象工厂（Abstract Factory） | 一族相关对象的创建 | 注入/替换工厂对象 |
| 建造者（Builder） | 复杂的多步骤构建 | 逐步构建，支持流式 API |
| 原型（Prototype） | 低成本地创建带有变化的副本 | 克隆已有实例 |
