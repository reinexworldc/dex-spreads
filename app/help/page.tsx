"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export default function HelpPage() {
  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight">Справка по DEX Spread Monitor</h1>
        <p className="text-muted-foreground">
          Руководство по использованию функций мониторинга спредов
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Основы использования</CardTitle>
          <CardDescription>
            Базовая информация о работе с приложением
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <section className="space-y-2">
            <h3 className="text-lg font-medium">Что такое спред?</h3>
            <p>
              Спред в контексте DEX бирж — это разница в цене одного и того же актива между разными биржами. 
              Эта разница выражается в процентах и рассчитывается по формуле:
              <br />
              <code className="bg-muted p-1 rounded">Спред (%) = (Цена_2 - Цена_1) / Цена_1 × 100%</code>
            </p>
          </section>
          
          <section className="space-y-2">
            <h3 className="text-lg font-medium">Как пользоваться графиком</h3>
            <ul className="list-disc pl-6 space-y-2">
              <li>
                <strong>Выбор инструмента:</strong> Используйте переключатели инструментов (Курсор, Рука, Масштаб)
                для управления графиком.
              </li>
              <li>
                <strong>Курсор:</strong> Режим просмотра графика без возможности масштабирования или перемещения.
              </li>
              <li>
                <strong>Рука:</strong> Позволяет перемещать график, удерживая левую кнопку мыши.
              </li>
              <li>
                <strong>Масштаб:</strong> Позволяет увеличивать/уменьшать участки графика. Можно использовать колесо мыши
                или выделять область для увеличения.
              </li>
              <li>
                <strong>Временные фреймы:</strong> Выберите подходящий временной интервал (от 1 минуты до 1 дня)
                для агрегации данных.
              </li>
              <li>
                <strong>Автообновление:</strong> Включите автообновление данных для получения актуальной информации
                в реальном времени.
              </li>
              <li>
                <strong>Экспорт данных:</strong> Используйте кнопку "Экспорт" для сохранения текущих данных графика
                в формате CSV.
              </li>
            </ul>
          </section>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader>
          <CardTitle>Настройки мониторинга</CardTitle>
          <CardDescription>
            Как настроить мониторинг под ваши потребности
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <section className="space-y-2">
            <h3 className="text-lg font-medium">Выбор пары токенов и бирж</h3>
            <p>
              На главной странице вы можете выбрать:
            </p>
            <ul className="list-disc pl-6 space-y-1">
              <li><strong>Пару токенов</strong> (например, ETH/USDT, BTC/USDT) для отслеживания спредов</li>
              <li><strong>Пару бирж</strong> для сравнения цен на выбранную пару токенов</li>
              <li><strong>Временной фрейм</strong> для агрегации данных и оптимального отображения</li>
            </ul>
            <p>
              После выбора настроек вы можете сохранить их кнопкой "Сохранить настройки". 
              При следующем открытии приложения эти настройки будут применены автоматически.
            </p>
          </section>
          
          <section className="space-y-2">
            <h3 className="text-lg font-medium">Интерпретация данных</h3>
            <ul className="list-disc pl-6 space-y-2">
              <li>
                <strong>Текущий спред:</strong> Показывает разницу в ценах между выбранными биржами на текущий момент.
              </li>
              <li>
                <strong>Максимальный спред:</strong> Наибольшая разница цен за выбранный период времени.
              </li>
              <li>
                <strong>Таблица спредов:</strong> Показывает текущие спреды между различными парами бирж, 
                с выделением выбранной пары.
              </li>
            </ul>
          </section>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader>
          <CardTitle>Арбитражные возможности</CardTitle>
          <CardDescription>
            Как использовать данные для арбитража между биржами
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <section className="space-y-2">
            <p>
              Арбитраж — это стратегия, при которой трейдер получает прибыль от разницы цен на один и тот же актив 
              на разных биржах. DEX Spread Monitor помогает обнаружить такие возможности:
            </p>
            <ul className="list-disc pl-6 space-y-2">
              <li>
                <strong>Показатель "Арбитраж"</strong> в таблице спредов указывает, на какой бирже выгоднее 
                купить актив.
              </li>
              <li>
                <strong>Большие спреды</strong> (более 1%) обычно указывают на арбитражные возможности, однако 
                учитывайте стоимость транзакции и время исполнения.
              </li>
              <li>
                <strong>История спредов</strong> на графике позволяет анализировать закономерности в колебаниях 
                цен между биржами.
              </li>
            </ul>
            <p>
              <strong>Обратите внимание:</strong> Арбитраж сопряжен с рисками. Учитывайте комиссии, время 
              подтверждения транзакций и другие факторы, прежде чем совершать арбитражные операции.
            </p>
          </section>
        </CardContent>
      </Card>
    </div>
  )
} 