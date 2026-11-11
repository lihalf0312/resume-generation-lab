# 审核结果到定向修订

此模块只消费已完成且版本绑定正确的完整审阅，不从词语猜事实，不自动改文，也不能把引用命中当作语义证明。

入口为 build_repair_plan(deliverable, receipt, source, runtime_date_basis)。返回 route：body_only、auxiliary_only、both、no_revision_needed 或 needs_review。can_dispatch 只说明已有可供受控修订的审核依据，不授予API或外部行动权限，不证明改后正确或最终验收。

每条反馈保留 reviewer_note、unit_snapshot、target_id、原目标文本/hash、原引用、完整源块和引用位置、相邻源块以及 related_units。相邻块只用于上下文。相关单位不是编辑目标，不能因为一条notes错就改动正确正文。标签映射回所属raw bullet，并以preserve_units保护未被指出问题的正文；正文修改同样保护正确标签。

缺审核、部分覆盖、陈旧绑定、个人事实歧义或缺少可定位依据，都给出明确pending，不调用修订callback。需要补证据或澄清时不得猜起始月、人物身份、能力或学历状态。明确正例如有据的leader/native/Proficient不被关键词阻止，是否有问题来自审阅者判断。

有一个窄的流程说明分支：selection_note被审核为当前上下文矛盾，且提供相关单位时，可以仅移除或改写为非断言指引。即使个人材料不证明这段流程历史，也不能凭空新增“已渲染”“已批准”“已通过”等事件。此分支不能用于改写个人事实或日期。

执行者必须遵守route和can_dispatch，限制PATCH目标ID，并核preserve_units完全不变。both缺任一执行入口时不得只发一半。每次修改后重建完整交付版本、重新源审、重新渲染变化正文/标签；不得复用旧receipt。预览与其他案例不受当前pending阻止。

回归夹具明确给出审核声明，仅验证证据保留、路由与保护机制，不测试模型是否能自主发现这些错误。已知真实失败只用于开发回放，不是盲测，也不进入生成prompt。
