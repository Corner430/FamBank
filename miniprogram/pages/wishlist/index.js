const { callCloud } = require('../../utils/cloud');
const { centsToYuan, yuanToCents } = require('../../utils/money');
const { isParent, isChild, getUserId, waitForLogin } = require('../../utils/auth');

Page({
  data: {
    childId: '',
    wishList: null,
    showCreateForm: false,
    newMaxPrice: '',
    newItems: [{ name: '', price: '', url: '' }],
    loading: true,
    isParentRole: false,
  },

  onLoad(options) {
    waitForLogin((user) => {
      if (!user) return;
      const childId = options.childId || getUserId();
      this.setData({
        childId,
        isParentRole: isParent(),
      });
      this.loadWishList();
    });
  },

  async loadWishList() {
    this.setData({ loading: true });
    try {
      const res = await callCloud('wishlist', 'get', { childId: this.data.childId });
      // Cloud function returns an array of wish lists, already yuan-formatted
      const lists = res || [];
      const activeList = lists.find(l => l.status === 'active') || lists[0] || null;
      if (activeList) {
        const items = (activeList.items || []).map(item => ({
          ...item,
          displayPrice: item.current_price,
          isTarget: item.id === activeList.active_target_item_id,
        }));
        this.setData({
          wishList: {
            ...activeList,
            displayMaxPrice: activeList.max_price,
            items,
            hasTarget: !!activeList.active_target_item_id,
          },
          loading: false,
        });
      } else {
        this.setData({ wishList: null, loading: false });
      }
    } catch (err) {
      console.error('加载愿望清单失败', err);
      wx.showToast({ title: '加载失败', icon: 'none' });
      this.setData({ loading: false });
    }
  },

  toggleCreateForm() {
    this.setData({
      showCreateForm: !this.data.showCreateForm,
      newMaxPrice: '',
      newItems: [{ name: '', price: '', url: '' }],
    });
  },

  onMaxPriceInput(e) {
    this.setData({ newMaxPrice: e.detail.value });
  },

  onItemNameInput(e) {
    const idx = e.currentTarget.dataset.idx;
    const key = `newItems[${idx}].name`;
    this.setData({ [key]: e.detail.value });
  },

  onItemPriceInput(e) {
    const idx = e.currentTarget.dataset.idx;
    const key = `newItems[${idx}].price`;
    this.setData({ [key]: e.detail.value });
  },

  onItemUrlInput(e) {
    const idx = e.currentTarget.dataset.idx;
    const key = `newItems[${idx}].url`;
    this.setData({ [key]: e.detail.value });
  },

  addItem() {
    const items = this.data.newItems.concat([{ name: '', price: '', url: '' }]);
    this.setData({ newItems: items });
  },

  removeItem(e) {
    const idx = e.currentTarget.dataset.idx;
    const items = this.data.newItems.filter((_, i) => i !== idx);
    if (items.length === 0) items.push({ name: '', price: '', url: '' });
    this.setData({ newItems: items });
  },

  async handleCreate() {
    const { newMaxPrice, newItems, childId } = this.data;
    if (!newMaxPrice) {
      wx.showToast({ title: '请输入最高价格', icon: 'none' });
      return;
    }
    const validItems = newItems.filter(i => i.name && i.price);
    if (validItems.length === 0) {
      wx.showToast({ title: '请至少添加一个商品', icon: 'none' });
      return;
    }
    try {
      // Validate locally, send yuan strings - cloud function does yuanToCents internally
      const maxPriceCheck = yuanToCents(newMaxPrice);
      if (maxPriceCheck <= 0) {
        wx.showToast({ title: '最高价格必须大于0', icon: 'none' });
        return;
      }
      const items = validItems.map(i => {
        const priceCheck = yuanToCents(i.price);
        if (priceCheck <= 0) throw new Error('商品价格必须大于0');
        return {
          name: i.name,
          price: i.price,
          url: i.url || '',
        };
      });
      await callCloud('wishlist', 'create', { childId, maxPrice: newMaxPrice, items });
      wx.showToast({ title: '创建成功', icon: 'success' });
      this.setData({ showCreateForm: false });
      this.loadWishList();
    } catch (err) {
      console.error('创建愿望清单失败', err);
      wx.showToast({ title: err.message || '创建失败', icon: 'none' });
    }
  },

  async handleDeclareTarget(e) {
    const itemId = e.currentTarget.dataset.itemId;
    try {
      await callCloud('wishlist', 'declareTarget', {
        childId: this.data.childId,
        wishListId: this.data.wishList.id,
        itemId,
      });
      wx.showToast({ title: '已设为标的', icon: 'success' });
      this.loadWishList();
    } catch (err) {
      console.error('设为标的失败', err);
      wx.showToast({ title: err.message || '操作失败', icon: 'none' });
    }
  },

  async handleClearTarget() {
    try {
      await callCloud('wishlist', 'clearTarget', {
        childId: this.data.childId,
        wishListId: this.data.wishList.id,
      });
      wx.showToast({ title: '已清除标的', icon: 'success' });
      this.loadWishList();
    } catch (err) {
      console.error('清除标的失败', err);
      wx.showToast({ title: err.message || '操作失败', icon: 'none' });
    }
  },

  handleUpdatePrice(e) {
    const itemId = e.currentTarget.dataset.itemId;
    const currentPrice = e.currentTarget.dataset.currentPrice;
    wx.showModal({
      title: '更新价格',
      content: '请输入新价格（元）',
      editable: true,
      placeholderText: String(currentPrice),
      success: async (res) => {
        if (res.confirm && res.content) {
          try {
            // Validate format, send yuan string - cloud function does yuanToCents internally
            const priceCheck = yuanToCents(res.content);
            if (priceCheck <= 0) {
              wx.showToast({ title: '价格必须大于0', icon: 'none' });
              return;
            }
            await callCloud('wishlist', 'updatePrice', { itemId, newPrice: res.content });
            wx.showToast({ title: '价格已更新', icon: 'success' });
            this.loadWishList();
          } catch (err) {
            console.error('更新价格失败', err);
            wx.showToast({ title: err.message || '更新失败', icon: 'none' });
          }
        }
      },
    });
  },

  onOpenUrl(e) {
    const url = e.currentTarget.dataset.url;
    if (url) {
      wx.setClipboardData({
        data: url,
        success: () => wx.showToast({ title: '链接已复制', icon: 'success' }),
      });
    }
  },
});
