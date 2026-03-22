## Lessons Learned

- 对于在独立 worktree 中开发的功能，不要凭感觉判断它是否已经进入 `main`；先用 `git rev-list --left-right --count main...<branch>` 或祖先关系检查确认真实分叉状态。
- 结束一个 worktree 功能时，验证要分两层：先看 feature 分支是否通过，再在合并后的 `main` 上重新跑一遍新鲜验证。
- `git worktree remove <path>` 之后，如果 Git 仍提示分支被 worktree 占用，先执行 `git worktree prune`，再删除分支。
