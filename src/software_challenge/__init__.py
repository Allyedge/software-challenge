import random
from socha import (
    GameState,
    Move,
    Hare,
    Advance,
    Field,
    FallBack,
    EatSalad,
    ExchangeCarrots,
    Card,
)
from socha.api.networking.game_client import IClientHandler
from socha.starter import Starter


class Logic(IClientHandler):
    gameState: GameState
    possible_moves: list[Move]
    current_player: Hare
    other_player: Hare
    finish_index = 64
    carrot_threshold_high = 60
    carrot_threshold_low = 20
    salad_threshold = 0
    fallback_carrot_gain_threshold = 35
    carrot_reserve_threshold = 60
    aggressive_distance_factor = 1.0

    def calculate_move(self) -> Move:
        print(self.possible_moves)
        finish_move = self.finish()
        if finish_move:
            print("FINISH")
            return finish_move

        salad_move = self.eat_salad()
        if salad_move:
            print("SALAD")
            return salad_move

        buy_salad_card_move = self.buy_salad_card_move()
        if buy_salad_card_move:
            print("BUY SALAD CARD")
            return buy_salad_card_move

        exchange_move = self.exchange_carrots_finish_area()
        if exchange_move:
            print("EXCHANGE")
            return exchange_move

        fallback_move = self.fallback()
        if fallback_move:
            print("FALLBACK")
            return fallback_move

        advance_move = self.advance()
        if advance_move:
            print("ADVANCE")
            return advance_move

        print("RANDOM")
        selected_move = random.choice(self.possible_moves)
        return selected_move

    def finish(self) -> Move:
        distance = self.finish_index - self.current_player.position
        carrot_cost = self.calculate_carrot_cost(distance)

        can_afford_finish = self.current_player.carrots - carrot_cost <= 10
        can_enter_finish = self.current_player.can_enter_goal()
        valid_carrots = self.current_player.carrots <= 10

        if can_afford_finish and can_enter_finish and valid_carrots:
            for move in self.possible_moves:
                if (
                        isinstance(move.action, Advance)
                        and move.action.distance == distance
                ):
                    return move
            return None
        else:
            return None

    def eat_salad(self) -> Move:
        if (
                self.current_player.salads > self.salad_threshold
                and self.gameState.board.get_field(self.current_player.position)
                == Field.Salad
        ):

            for move in self.possible_moves:
                if (
                        isinstance(move.action, Advance)
                        and Card.EatSalad in move.action.cards
                        and self.gameState.board.get_field(
                    self.current_player.position + move.action.distance
                )
                        != Field.Market
                        or isinstance(move.action, EatSalad)
                ):
                    return move

    def buy_salad_card_move(self) -> Move:
        possible_salad_buy_moves = [
            move
            for move in self.possible_moves
            if isinstance(move.action, Advance) and Card.EatSalad in move.action.cards
        ]

        if (
                possible_salad_buy_moves
                and self.current_player.salads > self.salad_threshold
                and self.current_player.salads - len(self.current_player.cards) > 0
        ):
            return possible_salad_buy_moves[0]

    def exchange_carrots_finish_area(self) -> Move:
        distance = self.finish_index - self.current_player.position
        carrot_cost = self.calculate_carrot_cost(distance)
        if (
                self.current_player.position == self.finish_index - 1
        ) and self.current_player.carrots > 10:
            possible_exchange_moves = [
                move
                for move in self.possible_moves
                if isinstance(move.action, ExchangeCarrots)
                   and move.action.amount == -10
            ]
            if possible_exchange_moves:
                return possible_exchange_moves[0]

        if (
                self.current_player.position == self.finish_index - 3
                and self.current_player.carrots > 10
                and self.current_player.carrots - carrot_cost <= 4
        ) or self.other_player.position == self.finish_index - 1:
            possible_exchange_moves = [
                move
                for move in self.possible_moves
                if isinstance(move.action, ExchangeCarrots)
                   and move.action.amount == -10
            ]
            if possible_exchange_moves:
                return possible_exchange_moves[0]

        # Patch to avoid fallback from 61st field
        if (
                self.current_player.carrots - self.calculate_carrot_cost(
            (self.finish_index - 1) - self.current_player.position) <= 10
        ):
            possible_moves = [
                move for move in self.possible_moves
                if isinstance(move.action, Advance) and move.action.distance == 2
            ]
            if possible_moves:
                return possible_moves[0]

    def fallback(self) -> Move:
        if self.current_player.carrots > self.fallback_carrot_gain_threshold:
            return None

        possible_fallback_moves = [
            move for move in self.possible_moves if isinstance(move.action, FallBack)
        ]
        if not possible_fallback_moves:
            return None

        if self.current_player.carrots > self.carrot_threshold_low:
            return None

        evaluated_moves = []
        for move in possible_fallback_moves:
            target_position = self.current_player.position - 1
            target_field = self.gameState.board.get_field(target_position)
            if target_position >= 0:
                field_value = 0
                if target_field == Field.Hedgehog:
                    field_value = 3
                elif target_field == Field.Position1 and self.current_player.is_ahead(
                        self.gameState
                ):
                    field_value = 2

                    if (
                            self.current_player.carrots
                            < self.fallback_carrot_gain_threshold
                    ):
                        field_value = 5
                elif (
                        target_field == Field.Position2
                        and not self.current_player.is_ahead(self.gameState)
                ):
                    field_value = 2

                    if (
                            self.current_player.carrots
                            < self.fallback_carrot_gain_threshold
                    ):
                        field_value = 5

                evaluated_moves.append((move, field_value))

        if evaluated_moves:
            best_fallback_move = max(evaluated_moves, key=lambda item: item[1])[0]
            if max(evaluated_moves, key=lambda item: item[1])[1] > 0:
                print(
                    f"SELECT FALLBACK MOVE WITH SCORE: {max(evaluated_moves, key=lambda item: item[1])[1]:.2f}"
                )
                return best_fallback_move

    def advance(self) -> Move:
        possible_advance_moves = [
            move for move in self.possible_moves if isinstance(move.action, Advance)
        ]
        if not possible_advance_moves:
            return None

        if self.current_player.salads >= self.salad_threshold:
            salad_moves = []
            for move in possible_advance_moves:
                target_position = self.current_player.position + move.action.distance
                if (
                        target_position < self.finish_index
                        and self.gameState.board.get_field(target_position) == Field.Salad
                ):
                    carrot_cost = self.calculate_carrot_cost(move.action.distance)
                    if self.current_player.carrots >= carrot_cost:
                        salad_moves.append(move)

            if salad_moves:
                print("PRIORTISE SALAD")
                return min(salad_moves, key=lambda move: move.action.distance)

        evaluated_moves = []
        for move in possible_advance_moves:
            carrot_cost = self.calculate_carrot_cost(move.action.distance)
            if self.current_player.carrots >= carrot_cost:
                target_position = self.current_player.position + move.action.distance
                if target_position < self.finish_index:
                    target_field = self.gameState.board.get_field(target_position)
                    field_value = 0
                    if target_field == Field.Salad:
                        field_value = 30
                    elif target_field == Field.Carrots:
                        field_value = 3

                        if target_position == self.finish_index - 3 and self.current_player.salads <= self.salad_threshold:
                            field_value = 10
                        elif target_position == self.finish_index - 3 and self.current_player.carrots - carrot_cost <= 20 and self.current_player.salads <= self.salad_threshold:
                            field_value = 20

                        if target_position == self.finish_index - 1 and self.current_player.salads <= self.salad_threshold:
                            field_value = 10
                        elif target_position == self.finish_index - 1 and self.current_player.carrots - carrot_cost <= 20 and self.current_player.carrots - carrot_cost >= 6 and self.current_player.salads <= self.salad_threshold:
                            field_value = 20

                    elif (
                            target_field == Field.Position1
                            and self.current_player.is_ahead(self.gameState)
                    ):
                        field_value = 7
                    elif (
                            target_field == Field.Position2
                            and not self.current_player.is_ahead(self.gameState)
                    ):
                        field_value = 7
                    elif target_field == Field.Hedgehog:
                        field_value = -3

                    value_per_carrot = (
                        field_value / carrot_cost if carrot_cost > 0 else 0
                    )
                    score = value_per_carrot

                    if self.current_player.carrots > self.carrot_reserve_threshold:
                        score += move.action.distance * self.aggressive_distance_factor

                    evaluated_moves.append((move, score))

        if evaluated_moves:
            best_move = max(evaluated_moves, key=lambda item: item[1])[0]
            print(
                f"SELECT ADVANCE MOVE WITH VALUE/CARROT: {max(evaluated_moves, key=lambda item: item[1])[1]:.2f}"
            )
            return best_move

    def calculate_carrot_cost(self, spaces: int) -> int:
        return spaces * (spaces + 1) // 2

    def on_update(self, state):
        self.gameState = state
        self.possible_moves = state.possible_moves()
        self.current_player = state.clone_current_player()
        self.other_player = state.clone_other_player()


if __name__ == "__main__":
    Starter(logic=Logic())
