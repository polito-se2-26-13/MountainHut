import { useEffect, useMemo, useState } from 'react';
import { Button, DatePicker, Form, Input, InputNumber, Modal, Select, TimePicker } from 'antd';
import dayjs from 'dayjs';
import { Navigate } from 'react-router';
import { apiRequest } from '../api/api.js';
import { useAuth } from '../auth/AuthContext.jsx';
import { useToast } from '../components/ToastProvider.jsx';
import { getSlotId, localDateString, normalizeSlots } from '../utils/slots.js';

const staffRoles = new Set(['Employee', 'Warden']);

function slotLabel(slot) {
  const mealType = slot.mealType ? ' · ' + slot.mealType : '';
  return slot.startTime + '–' + slot.endTime + mealType;
}

function keepEnterInField(event) {
  if (event.key === 'Enter' && event.target.closest('.ant-picker')) event.preventDefault();
}

function EmployeeSlotConfigPage() {
  const { session } = useAuth();
  const notify = useToast();
  const [slotDate, setSlotDate] = useState(localDateString());
  const [timeSlots, setTimeSlots] = useState([]);
  const [tables, setTables] = useState([]);
  const [selectedTimeId, setSelectedTimeId] = useState('');
  const [selectedTableIds, setSelectedTableIds] = useState([]);
  const [copySourceOptions, setCopySourceOptions] = useState([]);
  const [selectedSourceSlotId, setSelectedSourceSlotId] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [newTimeOpen, setNewTimeOpen] = useState(false);
  const [newTableOpen, setNewTableOpen] = useState(false);
  const [newTimeForm] = Form.useForm();
  const [newTableForm] = Form.useForm();

  useEffect(() => {
    if (!session?.isAuthenticated || !staffRoles.has(session.userProfile.role)) return undefined;
    let active = true;
    queueMicrotask(() => { if (active) setIsLoading(true); });
    Promise.all([
      apiRequest('/slots/times', { headers: { Authorization: `Bearer ${session.token}` } }),
      apiRequest('/slots/tables', { headers: { Authorization: `Bearer ${session.token}` } }),
      apiRequest(`/slots?date=${encodeURIComponent(slotDate)}`, { headers: { Authorization: `Bearer ${session.token}` } }),
    ]).then(([times, physicalTables, savedSlots]) => {
      if (!active) return;
      setTimeSlots(Array.isArray(times) ? times : []);
      setTables(Array.isArray(physicalTables) ? physicalTables : []);
      setCopySourceOptions(normalizeSlots(savedSlots));
      setSelectedSourceSlotId('');
      setSelectedTableIds([]);
      setSelectedTimeId('');
    }).catch(error => {
      if (active) notify(error.message || 'Could not load service times and tables.');
    }).finally(() => { if (active) setIsLoading(false); });
    return () => { active = false; };
  }, [session, slotDate, notify]);

  const availableTimeSlots = useMemo(
    () => timeSlots.filter(slot => !slot.date || slot.date === slotDate),
    [timeSlots, slotDate]
  );
  const selectedTables = tables.filter(table => selectedTableIds.includes(String(table.id)));
  const totalCapacity = selectedTables.reduce((total, table) => total + Number(table.capacity ?? table.seats ?? 0), 0);

  if (!session?.isAuthenticated || !staffRoles.has(session.userProfile.role)) return <Navigate to="/login" replace />;

  function createTime(values) {
    const draftSlot = {
      id: `draft-time-${Date.now()}`,
      date: slotDate,
      startTime: values.startTime.format('HH:mm'),
      endTime: values.endTime.format('HH:mm'),
      mealType: values.mealType,
      isDraft: true,
    };
    setTimeSlots(current => [...current, draftSlot]);
    setSelectedTimeId(String(draftSlot.id));
    setNewTimeOpen(false);
    newTimeForm.resetFields();
    notify('Service time added to this unsaved configuration.', 'success');
  }

  function createTable(values) {
    const duplicate = tables.some(table => table.tableNumber.trim().toLowerCase() === values.tableNumber.trim().toLowerCase());
    if (duplicate) {
      newTableForm.setFields([{ name: 'tableNumber', errors: ['This table number already exists.'] }]);
      return;
    }
    const draftTable = {
      id: `draft-table-${Date.now()}`,
      tableNumber: values.tableNumber.trim(),
      capacity: values.capacity,
      location: (values.location || '').trim(),
      isDraft: true,
    };
    setTables(current => [...current, draftTable]);
    setSelectedTableIds(current => [...current, String(draftTable.id)]);
    setNewTableOpen(false);
    newTableForm.resetFields();
    notify('Table added to this unsaved configuration.', 'success');
  }

  function copyTables() {
    if (!selectedSourceSlotId) { notify('Choose a saved time slot to copy first.'); return; }
    const source = copySourceOptions.find(slot => String(getSlotId(slot)) === String(selectedSourceSlotId));
    if (!source) { notify('The selected saved time slot is no longer available.'); return; }
    const ids = new Set(source.tables.map(table => String(table.id ?? table.tableId ?? '')));
    const numbers = new Set(source.tables.map(table => String(table.tableNumber).toLowerCase()));
    setSelectedTableIds(tables.filter(table => ids.has(String(table.id)) || numbers.has(String(table.tableNumber).toLowerCase())).map(table => String(table.id)));
    notify(`Selected ${source.tables.length} table${source.tables.length === 1 ? '' : 's'} from the saved slot.`, 'success');
  }

  async function handleSubmit() {
    const selectedTime = availableTimeSlots.find(slot => String(slot.id) === String(selectedTimeId));
    if (!selectedTime) { notify('Choose a defined service time first.'); return; }
    if (!selectedTables.length) { notify('Select at least one table for this time slot.'); return; }
    setIsSaving(true);
    try {
      await apiRequest('/slots', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${session.token}` },
        body: JSON.stringify({
          date: slotDate,
          startTime: selectedTime.startTime,
          endTime: selectedTime.endTime,
          ...(selectedTime.mealType ? { mealType: selectedTime.mealType } : {}),
          tables: selectedTables.map(table => ({
            tableNumber: table.tableNumber,
            seats: Number(table.capacity ?? table.seats),
            ...(table.location ? { location: table.location } : {}),
          })),
        }),
      });
      notify('Time slot and table configuration saved.', 'success');
      const savedSlots = await apiRequest(`/slots?date=${encodeURIComponent(slotDate)}`, { headers: { Authorization: `Bearer ${session.token}` } });
      setCopySourceOptions(normalizeSlots(savedSlots));
    } catch (error) { notify(error.message || 'Could not save this time slot.'); }
    finally { setIsSaving(false); }
  }

  return (
    <main className="page slot-page">
      <header className="slot-page-header">
        <div><p className="eyebrow">MOUNTAINHUT · EMPLOYEE TOOLS</p><h1>Service slots &amp; table setup</h1><p className="form-intro">Choose a defined service time and the physical tables available on that date.</p></div>
        <div className="capacity-card" aria-live="polite"><span>Total capacity</span><strong>{totalCapacity}</strong><small>seats in this slot</small></div>
      </header>

      <Form className="slot-form mh-form" onFinish={handleSubmit} onKeyDown={keepEnterInField} noValidate>
        <section className="slot-panel" aria-labelledby="slot-details-title">
          <div className="section-heading"><div><span className="section-step">01</span><h2 id="slot-details-title">Service time</h2></div><p>Choose a saved service time or define a new one.</p></div>
          <div className="slot-form-grid">
            <label className="form-field"><span>Date <span className="required-mark">*</span></span><DatePicker className="mh-control" format="YYYY-MM-DD" value={slotDate ? dayjs(slotDate) : null} onChange={date => setSlotDate(date ? date.format('YYYY-MM-DD') : '')} allowClear={false} /></label>
            <label className="form-field"><span>Defined service time <span className="required-mark">*</span></span><Select className="mh-control" value={selectedTimeId || undefined} placeholder={isLoading ? 'Loading service times…' : 'Choose a service time'} onChange={setSelectedTimeId} loading={isLoading} options={availableTimeSlots.map(slot => ({ value: String(slot.id), label: slotLabel(slot) }))} /></label>
            <div className="form-field slot-definition-action"><span aria-hidden="true">&nbsp;</span><Button className="add-table-button define-slot-button" htmlType="button" onClick={() => setNewTimeOpen(true)}>+ Define a new slot</Button></div>
          </div>
        </section>

        <section className="slot-panel" aria-labelledby="tables-title">
          <div className="section-heading"><div><span className="section-step">02</span><h2 id="tables-title">Available tables</h2></div><p>Table capacity is fixed when the physical table is created.</p></div>
          <div className="copy-toolbar">
            <label className="form-field copy-select-field"><span>Copy table selection from a saved slot</span><Select className="mh-control" value={selectedSourceSlotId || undefined} placeholder={copySourceOptions.length ? 'Choose a saved time slot' : 'No saved slots for this date'} onChange={setSelectedSourceSlotId} disabled={isLoading || !copySourceOptions.length} options={copySourceOptions.map(slot => ({ value: String(getSlotId(slot)), label: `${slot.date} ${slotLabel(slot)}` }))} /></label>
            <Button className="secondary-button copy-button" htmlType="button" onClick={copyTables} disabled={isLoading || !copySourceOptions.length}>Copy table selection</Button>
          </div>
          {tables.length ? <fieldset className="table-list">
            <legend className="sr-only">Defined tables</legend>
            {tables.map(table => {
              const selected = selectedTableIds.includes(String(table.id));
              return <button
                className={`table-row table-choice-card${selected ? ' table-choice-card-selected' : ''}`}
                type="button"
                key={table.id}
                aria-pressed={selected}
                onClick={() => setSelectedTableIds(current => selected ? current.filter(id => id !== String(table.id)) : [...current, String(table.id)])}
              >
                <span className="table-index">{table.tableNumber}</span><span>{table.capacity ?? table.seats} seats{table.location ? ` · ${table.location}` : ''}</span>
              </button>;
            })}
          </fieldset> : <div className="empty-tables"><strong>No defined tables yet</strong><span>Create a physical table to add it to the checklist.</span></div>}
          <div className="table-actions">
            <Button className="secondary-button clear-selection-button" htmlType="button" onClick={() => setSelectedTableIds([])} disabled={!selectedTableIds.length}>Clear selection</Button>
            <Button className="add-table-button" htmlType="button" onClick={() => setNewTableOpen(true)}>+ Define a new table</Button>
          </div>
        </section>

        <footer className="slot-form-footer"><span>Selected tables: {selectedTables.length} · Capacity: {totalCapacity} seats</span><Button className="submit-button save-slot-button" type="primary" htmlType="submit" loading={isSaving}>Save time slot</Button></footer>
      </Form>

      <Modal title="Define a new service time" open={newTimeOpen} onCancel={() => setNewTimeOpen(false)} footer={null} destroyOnHidden>
        <Form form={newTimeForm} layout="vertical" onFinish={createTime}>
          <Form.Item name="startTime" label="Starting time" rules={[{ required: true }]}><TimePicker className="mh-control" format="HH:mm" /></Form.Item>
          <Form.Item name="endTime" label="Ending time" rules={[{ required: true }, ({ getFieldValue }) => ({ validator(_, value) { const start = getFieldValue('startTime'); return !start || !value || value.isAfter(start) ? Promise.resolve() : Promise.reject(new Error('End time must be later than start time.')); } })]}><TimePicker className="mh-control" format="HH:mm" /></Form.Item>
          <Form.Item name="mealType" label="Meal type" rules={[{ required: true }]}><Select options={['Lunch', 'Dinner', 'Snack'].map(value => ({ value, label: value }))} /></Form.Item>
          <Button type="primary" htmlType="submit">Create service time</Button>
        </Form>
      </Modal>

      <Modal title="Define a new table" open={newTableOpen} onCancel={() => setNewTableOpen(false)} footer={null} destroyOnHidden>
        <Form form={newTableForm} layout="vertical" onFinish={createTable}>
          <Form.Item name="tableNumber" label="Table number" rules={[{ required: true }, { whitespace: true, message: 'Enter a table number.' }]}><Input placeholder="e.g. T10" /></Form.Item>
          <Form.Item name="capacity" label="Fixed seats" rules={[{ required: true }]}><InputNumber min={1} step={1} className="mh-control" /></Form.Item>
          <Form.Item name="location" label="Location (optional)"><Input placeholder="e.g. Terrace" /></Form.Item>
          <Button type="primary" htmlType="submit">Create table</Button>
        </Form>
      </Modal>
    </main>
  );
}

export default EmployeeSlotConfigPage;
