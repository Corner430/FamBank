Component({
  properties: {
    children: {
      type: Array,
      value: [],
    },
    selectedId: {
      type: Number,
      value: 0,
    },
  },

  methods: {
    onSelectChild(e) {
      const childId = e.currentTarget.dataset.id;
      this.triggerEvent('select', { childId });
    },
  },
});
