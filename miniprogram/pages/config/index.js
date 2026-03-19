const { callCloud } = require('../../utils/cloud');
const { waitForLogin, requireParent } = require('../../utils/auth');

// Config display metadata
const CONFIG_META = {
  split_ratio_a: { label: 'A 分流比例', unit: '%', group: '收入分流' },
  split_ratio_b: { label: 'B 分流比例', unit: '%', group: '收入分流' },
  split_ratio_c: { label: 'C 分流比例', unit: '%', group: '收入分流' },
  b_tier1_rate: { label: 'B 第一档利率', unit: 'BP', group: 'B 利率' },
  b_tier1_limit: { label: 'B 第一档上限', unit: '分', group: 'B 利率', isCents: true },
  b_tier2_rate: { label: 'B 第二档利率', unit: 'BP', group: 'B 利率' },
  b_tier3_rate: { label: 'B 第三档利率', unit: 'BP', group: 'B 利率' },
  c_annual_rate: { label: 'C 年化利率', unit: 'BP', group: 'C 利率' },
  penalty_multiplier: { label: '违约罚金倍数', unit: '倍', group: '违约' },
  redemption_fee_rate: { label: 'C 赎回费率', unit: '%', group: 'C 赎回' },
  wishlist_lock_months: { label: '愿望锁定期', unit: '月', group: '愿望清单' },
  wishlist_valid_months: { label: '愿望有效期', unit: '月', group: '愿望清单' },
  b_suspend_months: { label: 'B 暂停窗口', unit: '月', group: '违约' },
  c_lock_age: { label: 'C 解锁年龄', unit: '岁', group: 'C 赎回' },
};

Page({
  data: {
    config: null,
    configGroups: [],
    announcements: [],
    loading: true,
    // Announce form
    showAnnounceForm: false,
    announceKey: '',
    announceLabel: '',
    announceNewValue: '',
    announceLoading: false,
  },

  onLoad() {
    waitForLogin(() => {
      if (!requireParent()) return;
      this.loadData();
    });
  },

  async loadData() {
    this.setData({ loading: true });
    try {
      const [config, announcements] = await Promise.all([
        callCloud('config', 'list'),
        callCloud('config', 'listAnnouncements'),
      ]);
      this.setData({
        config,
        configGroups: this.buildGroups(config),
        announcements: announcements || [],
      });
    } catch (err) {
      console.error('加载配置失败:', err);
    } finally {
      this.setData({ loading: false });
    }
  },

  buildGroups(config) {
    const groupMap = {};
    const groupOrder = [];
    for (const [key, meta] of Object.entries(CONFIG_META)) {
      const group = meta.group;
      if (!groupMap[group]) {
        groupMap[group] = [];
        groupOrder.push(group);
      }
      const value = config[key];
      let displayValue = String(value);
      if (meta.isCents) {
        displayValue = (value / 100).toFixed(2) + ' 元';
      } else if (meta.unit === 'BP') {
        displayValue = (value / 100).toFixed(2) + '%';
      } else {
        displayValue = value + meta.unit;
      }
      groupMap[group].push({
        key,
        label: meta.label,
        value,
        displayValue,
        unit: meta.unit,
      });
    }
    return groupOrder.map((name) => ({ name, items: groupMap[name] }));
  },

  openAnnounceForm(e) {
    const { key, label } = e.currentTarget.dataset;
    this.setData({
      showAnnounceForm: true,
      announceKey: key,
      announceLabel: label,
      announceNewValue: '',
    });
  },

  closeAnnounceForm() {
    this.setData({
      showAnnounceForm: false,
      announceKey: '',
      announceLabel: '',
      announceNewValue: '',
    });
  },

  onAnnounceValueInput(e) {
    this.setData({ announceNewValue: e.detail.value });
  },

  async handleAnnounce() {
    const { announceKey, announceNewValue, announceLoading } = this.data;
    if (announceLoading) return;

    if (!announceNewValue || isNaN(parseInt(announceNewValue))) {
      wx.showToast({ title: '请输入有效的整数值', icon: 'none' });
      return;
    }

    this.setData({ announceLoading: true });
    try {
      await callCloud('config', 'announce', {
        key: announceKey,
        newValue: parseInt(announceNewValue),
      });
      wx.showToast({ title: '公告已发布', icon: 'success' });
      this.closeAnnounceForm();
      this.loadData();
    } catch (err) {
      console.error('发布公告失败:', err);
    } finally {
      this.setData({ announceLoading: false });
    }
  },
});
