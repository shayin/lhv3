请你帮我检索codebase，并生成.cursorrules以及.cursorignore文件

请你在执行操作前，先复述一遍我的需求再进行操作，让我先确认你清楚我的需求

需求正确，请你一步一步帮我执行


```
想法及要求
```
我想要一个带界面的量化系统，可以支持配置策略，也支持回测策略的效果，请你作为产品专家，帮我完成需求的梳理，并将内容填充到文件`idea.md`中。


基于文件`idea.md`里面的需求内容，帮我完成一期的开发

1、后端回测时，购买的数量应该是整数
2、前端回测界面的交易明细，增加购买或者出售的数量和金额

1、回测界面交易明细显示的收益率，应该由后端返回为准
2、回测界面显示的年化收益率、最大回测、夏普比率、胜率、盈亏比、Aplha、Beta、交易次数，也应该由后端返回为准




策略收益曲线做以下优化：
1、增加买卖点，参照K线的买卖点做标记
2、也标记出最大回测的最高点和最低点


1、点击策略编辑时，前端界面的策略参数详情应该由后端接口返回，请修正这个问题。
2、后端所有请求数据库的地方都要打印出sql语句

策略编辑器的页面，缺少了策略的列表，应该点击后默认从后端的数据库获取策略列表，再点击具体某个策略查看策略参数，并做增删改查

帮我集成到平台里，但我有几个要求：
1、用户编写的代码要放在后端数据库里，前端请求后端返回对应的策略代码展示在界面上
2、策略的实现要有规范，比如必须实现什么python方法，return的协议也要固定，这个在保存策略代码时，后端要做好校验确保实现正确

现在回测用的数据是靠前端传过来的，应该改成后端根据回测的交易品种，去数据库查到回测用的数据