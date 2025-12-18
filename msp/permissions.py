from accounts.permissions import HasMinAccessLevel

AdminOnly = HasMinAccessLevel.with_level('admin')
MemberOrAbove = HasMinAccessLevel.with_level('member')
