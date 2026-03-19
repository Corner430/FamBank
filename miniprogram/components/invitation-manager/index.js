const { callCloud } = require('../../utils/cloud');

Component({
  properties: {},

  data: {
    invitations: [],
    showCreateForm: false,
    targetRole: 'child',
    targetName: '',
    loading: false,
  },

  lifetimes: {
    attached() {
      this.loadInvitations();
    },
  },

  methods: {
    async loadInvitations() {
      this.setData({ loading: true });
      try {
        const data = await callCloud('family', 'listInvitations');
        this.setData({ invitations: data || [] });
      } catch (err) {
        console.error('[invitation-manager] loadInvitations error:', err);
      } finally {
        this.setData({ loading: false });
      }
    },

    toggleCreateForm() {
      this.setData({
        showCreateForm: !this.data.showCreateForm,
        targetRole: 'child',
        targetName: '',
      });
    },

    onRoleChange(e) {
      this.setData({ targetRole: e.detail.value });
    },

    onNameInput(e) {
      this.setData({ targetName: e.detail.value });
    },

    async createInvitation() {
      const { targetRole, targetName } = this.data;
      if (!targetName.trim()) {
        wx.showToast({ title: '请输入名称', icon: 'none' });
        return;
      }
      try {
        await callCloud('family', 'createInvitation', {
          targetRole,
          targetName: targetName.trim(),
        });
        wx.showToast({ title: '创建成功', icon: 'success' });
        this.setData({ showCreateForm: false, targetName: '' });
        this.loadInvitations();
      } catch (err) {
        console.error('[invitation-manager] createInvitation error:', err);
      }
    },

    async revokeInvitation(e) {
      const id = e.currentTarget.dataset.id;
      try {
        await callCloud('family', 'revokeInvitation', { invitationId: id });
        wx.showToast({ title: '已撤销', icon: 'success' });
        this.loadInvitations();
      } catch (err) {
        console.error('[invitation-manager] revokeInvitation error:', err);
      }
    },

    copyCode(e) {
      const code = e.currentTarget.dataset.code;
      wx.setClipboardData({
        data: code,
        success() {
          wx.showToast({ title: '邀请码已复制', icon: 'success' });
        },
      });
    },

    formatDate(ts) {
      if (!ts) return '';
      const d = new Date(ts);
      const mm = String(d.getMonth() + 1).padStart(2, '0');
      const dd = String(d.getDate()).padStart(2, '0');
      return d.getFullYear() + '-' + mm + '-' + dd;
    },
  },
});
