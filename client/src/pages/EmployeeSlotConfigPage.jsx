import { useEffect, useMemo, useState } from 'react';
import { Button, DatePicker, Form, Input, InputNumber, Select, TimePicker } from 'antd';
import dayjs from 'dayjs';
import { Navigate } from 'react-router';
import { apiRequest } from '../api/api.js';
import { useAuth } from '../auth/AuthContext.jsx';
import { useToast } from '../components/ToastProvider.jsx';
import { getSlotId, localDateString, normalizeSlots } from '../utils/slots.js';

// the id only tells the rows of this form apart, so a counter is enough
let nextTableId = 1;

function createTable(tableNumber = '', seats = 2) {
  return {
    id: nextTableId++,
    tableNumber,
    seats,
  };
}

function slotLabel(slot) {
  const seats = slot.tables.reduce((sum, table) => sum + table.seats, 0);
  return `${slot.date} ${slot.startTime}–${slot.endTime} (${slot.tables.length} tables / ${seats} seats)`;
}

// the warden manages the hut, so they set up times and tables like an employee
const staffRoles = ['Employee', 'Warden'];

// Enter in a date or time field confirms that value only, it must not send the half-filled form;
// it runs on the form, after the picker has already taken the typed value
function keepEnterInField(event) {
  if (event.key === 'Enter' && event.target.closest('.ant-picker')) event.preventDefault();
}

function EmployeeSlotConfigPage() {
  const { session } = useAuth();
  const [formData, setFormData] = useState({
    slotDate: localDateString(),
    startTime: '',
    endTime: '',
    mealType: '',
    tables: [],
  });
  const [copySourceOptions, setCopySourceOptions] = useState([]);
  const [selectedSourceSlotId, setSelectedSourceSlotId] = useState('');
  const [isLoadingSources, setIsLoadingSources] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [sourceRefreshKey, setSourceRefreshKey] = useState(0);
  const notify = useToast();

  useEffect(() => {
    if (!session?.isAuthenticated || !staffRoles.includes(session.userProfile.role)) return undefined;
    let active = true;
    queueMicrotask(() => {
      if (active) {
        setIsLoadingSources(true);
        setCopySourceOptions([]);
        setSelectedSourceSlotId('');
      }
    });
    apiRequest(`/slots?date=${encodeURIComponent(formData.slotDate)}`, {
      headers: { Authorization: `Bearer ${session.token}` },
    })
      .then(result => {
        if (active) setCopySourceOptions(normalizeSlots(result));
      })
      .catch(error => {
        if (active) notify(error.message || 'Could not load saved time slots.');
      })
      .finally(() => {
        if (active) setIsLoadingSources(false);
      });
    return () => {
      active = false;
    };
  }, [formData.slotDate, session, sourceRefreshKey, notify]);

  const totalCapacity = useMemo(
    () => formData.tables.reduce((total, table) => total + (Number(table.seats) || 0), 0),
    [formData.tables]
  );

  if (!session?.isAuthenticated || !staffRoles.includes(session.userProfile.role)) {
    return <Navigate to="/login" replace />;
  }

  function updateForm(field, value) {
    setFormData(current => ({ ...current, [field]: value }));
  }

  function updateTable(tableId, field, value) {
    setFormData(current => ({
      ...current,
      tables: current.tables.map(table =>
        table.id === tableId ? { ...table, [field]: value } : table
      ),
    }));
  }

  function addTable() {
    setFormData(current => ({ ...current, tables: [...current.tables, createTable()] }));
  }

  function removeTable(tableId) {
    setFormData(current => ({
      ...current,
      tables: current.tables.filter(table => table.id !== tableId),
    }));
  }

  function copyTables() {
    if (!selectedSourceSlotId) {
      notify('Choose a saved time slot to copy first.');
      return;
    }
    const source = copySourceOptions.find(
      slot => String(getSlotId(slot)) === String(selectedSourceSlotId)
    );
    if (!source) {
      notify('The selected saved time slot is no longer available.');
      return;
    }
    setFormData(current => ({
      ...current,
      tables: source.tables.map(table => createTable(table.tableNumber, table.seats)),
    }));
    notify(`Copied ${source.tables.length} table${source.tables.length === 1 ? '' : 's'} from the selected time slot.`, 'success');
  }

  function validate() {
    if (!formData.slotDate || !formData.startTime || !formData.endTime)
      return 'Date, start time, and end time are required.';
    if (formData.startTime >= formData.endTime) return 'End time must be later than start time.';
    if (formData.tables.length === 0) return 'Add at least one table to this time slot.';
    if (formData.tables.some(table => !String(table.tableNumber).trim()))
      return 'Enter a number for every table.';
    if (
      formData.tables.some(
        table => !Number.isInteger(Number(table.seats)) || Number(table.seats) < 1
      )
    )
      return 'Each table must have at least one seat.';
    const numbers = formData.tables.map(table => String(table.tableNumber).trim().toLowerCase());
    if (new Set(numbers).size !== numbers.length)
      return 'Table numbers must be unique within this time slot.';
    return '';
  }

  async function handleSubmit() {
    const validationMessage = validate();
    if (validationMessage) {
      notify(validationMessage);
      return;
    }

    setIsSaving(true);
    try {
      await apiRequest('/slots', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${session.token}`,
        },
        body: JSON.stringify({
          date: formData.slotDate,
          startTime: formData.startTime,
          endTime: formData.endTime,
          ...(formData.mealType ? { mealType: formData.mealType } : {}),
          tables: formData.tables.map(({ tableNumber, seats }) => ({
            tableNumber: String(tableNumber).trim(),
            seats: Number(seats),
          })),
        }),
      });
      notify('Time slot and table configuration saved.', 'success');
      setSourceRefreshKey(current => current + 1);
    } catch (error) {
      notify(error.message || 'Could not save this time slot.');
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <main className="page slot-page">
      <header className="slot-page-header">
        <div>
          <p className="eyebrow">MOUNTAINHUT · EMPLOYEE TOOLS</p>
          <h1>Service slots &amp; table setup</h1>
          <p className="form-intro">Set service times and build a table layout for any date.</p>
        </div>
        <div className="capacity-card" aria-live="polite">
          <span>Total capacity</span>
          <strong>{totalCapacity}</strong>
          <small>seats in this slot</small>
        </div>
      </header>

      <Form className="slot-form mh-form" onFinish={handleSubmit} onKeyDown={keepEnterInField} noValidate>
        <section className="slot-panel" aria-labelledby="slot-details-title">
          <div className="section-heading">
            <div>
              <span className="section-step">01</span>
              <h2 id="slot-details-title">Service time</h2>
            </div>
            <p>Create multiple service rounds on the same date.</p>
          </div>

          <div className="slot-form-grid">
            <label className="form-field">
              <span>
                Date{' '}
                <span className="required-mark" aria-hidden="true">
                  *
                </span>
              </span>
              <DatePicker
                className="mh-control"
                format="YYYY-MM-DD"
                value={formData.slotDate ? dayjs(formData.slotDate) : null}
                onChange={date => updateForm('slotDate', date ? date.format('YYYY-MM-DD') : '')}
                allowClear={false}
              />
            </label>
            <label className="form-field">
              <span>
                Starting time{' '}
                <span className="required-mark" aria-hidden="true">
                  *
                </span>
              </span>
              <TimePicker
                className="mh-control"
                format="HH:mm"
                value={formData.startTime ? dayjs(`2000-01-01T${formData.startTime}`) : null}
                onChange={time => updateForm('startTime', time ? time.format('HH:mm') : '')}
                allowClear
              />
            </label>
            <label className="form-field">
              <span>
                Ending time{' '}
                <span className="required-mark" aria-hidden="true">
                  *
                </span>
              </span>
              <TimePicker
                className="mh-control"
                format="HH:mm"
                value={formData.endTime ? dayjs(`2000-01-01T${formData.endTime}`) : null}
                onChange={time => updateForm('endTime', time ? time.format('HH:mm') : '')}
                allowClear
              />
            </label>
            <label className="form-field">
              <span>
                Meal type <span className="optional-mark">(optional)</span>
              </span>
              <Select
                className="mh-control"
                value={formData.mealType || undefined}
                placeholder="Select a meal type"
                onChange={value => updateForm('mealType', value || '')}
                options={[
                  { value: 'Lunch', label: 'Lunch' },
                  { value: 'Dinner', label: 'Dinner' },
                  { value: 'Snack', label: 'Snack' },
                ]}
              />
            </label>
          </div>
        </section>

        <section className="slot-panel" aria-labelledby="tables-title">
          <div className="section-heading">
            <div>
              <span className="section-step">02</span>
              <h2 id="tables-title">Tables &amp; seats</h2>
            </div>
            <p>Choose a layout that fits this date and service.</p>
          </div>

          <div className="copy-toolbar">
            <label className="form-field copy-select-field">
              <span>Copy the tables of a previous slot</span>
              <Select
                className="mh-control"
                value={selectedSourceSlotId || undefined}
                placeholder={isLoadingSources
                  ? 'Loading saved slots…'
                  : copySourceOptions.length
                    ? 'Choose a saved time slot'
                    : 'No saved slots for this date'}
                onChange={value => setSelectedSourceSlotId(value)}
                disabled={isLoadingSources || copySourceOptions.length === 0}
                loading={isLoadingSources}
                options={copySourceOptions.map(slot => ({
                  value: String(getSlotId(slot)),
                  label: slotLabel(slot),
                }))}
              />
            </label>
            <Button
              className="secondary-button copy-button"
              htmlType="button"
              onClick={copyTables}
              disabled={isLoadingSources || !copySourceOptions.length}
            >
              Copy table configuration
            </Button>
          </div>

          <div className="table-list-heading" aria-hidden="true">
            <span>Table number</span>
            <span>Seats</span>
            <span />
          </div>
          {formData.tables.length === 0 ? (
            <div className="empty-tables">
              <strong>No tables added yet</strong>
              <span>Add a table or copy a saved configuration to get started.</span>
            </div>
          ) : (
            <div className="table-list">
              {formData.tables.map((table, index) => (
                <div className="table-row" key={table.id}>
                  <span className="table-index">{String(index + 1).padStart(2, '0')}</span>
                  <label className="sr-only" htmlFor={`table-number-${table.id}`}>
                    Table number {index + 1}
                  </label>
                  <Input
                    className="mh-control"
                    id={`table-number-${table.id}`}
                    value={table.tableNumber}
                    placeholder="e.g. T1"
                    onChange={event => updateTable(table.id, 'tableNumber', event.target.value)}
                    aria-label={`Table number ${index + 1}`}
                  />
                  <label className="sr-only" htmlFor={`table-seats-${table.id}`}>
                    Seats at table {index + 1}
                  </label>
                  <InputNumber
                    className="mh-control"
                    id={`table-seats-${table.id}`}
                    min={1}
                    step={1}
                    value={table.seats}
                    onChange={value => updateTable(table.id, 'seats', value ?? '')}
                    aria-label={`Seats at table ${index + 1}`}
                  />
                  <Button
                    className="remove-table-button"
                    htmlType="button"
                    onClick={() => removeTable(table.id)}
                    aria-label={`Remove table ${index + 1}`}
                  >
                    Remove
                  </Button>
                </div>
              ))}
            </div>
          )}
          <Button className="add-table-button" htmlType="button" onClick={addTable}>
            + Add a table
          </Button>
        </section>

        <footer className="slot-form-footer">
          <span>Changes are saved to the selected date and time.</span>
          <Button className="submit-button save-slot-button" type="primary" htmlType="submit" loading={isSaving}>
            {isSaving ? 'Saving configuration…' : 'Save time slot'}
          </Button>
        </footer>
      </Form>
    </main>
  );
}

export default EmployeeSlotConfigPage;
